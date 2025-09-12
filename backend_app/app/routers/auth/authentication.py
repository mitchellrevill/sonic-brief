"""
Authentication Router - Core authentication operations
Handles login, logout, and token management
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import logging
import uuid

from ...core.config import get_app_config, get_cosmos_db_cached, CosmosDB, DatabaseError
from ...services.content import AnalyticsService

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(prefix="", tags=["authentication"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: str | None = None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, config: Any) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=config.auth["jwt_access_token_expire_minutes"]
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, config.auth["jwt_secret_key"], algorithm=config.auth["jwt_algorithm"]
    )
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    config = get_app_config()
    cosmos_db = get_cosmos_db_cached(config)

    try:
        logger.debug("Attempting to decode JWT token")
        payload = jwt.decode(
            token,
            config.auth["jwt_secret_key"],
            algorithms=[config.auth["jwt_algorithm"]],
        )
        email: str = payload.get("sub")
        if email is None:
            logger.error("No email found in JWT payload")
            raise credentials_exception
        logger.debug(f"JWT decoded successfully for email: {email}")
        token_data = TokenData(email=email)
    except JWTError as e:
        logger.error(f"JWT decode error: {str(e)}")
        raise credentials_exception

    try:
        logger.debug(f"Looking up user by email: {token_data.email}")
        user = await cosmos_db.get_user_by_email(email=token_data.email)
        if user is None:
            logger.error(f"User not found in database: {token_data.email}")
            raise credentials_exception
        logger.debug(f"User found successfully: {user.get('id', 'unknown')}")
        return user
    except Exception as e:
        logger.error(f"Database error during user lookup: {str(e)}")
        raise credentials_exception


async def authenticate_user(
    cosmos_db: CosmosDB, email: str, password: str
) -> Dict[str, Any] | bool:
    """Authenticate user credentials."""
    user = await cosmos_db.get_user_by_email(email)
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return user


@router.post("/login")
async def login_for_access_token(request: Request):
    """Handle user login and token generation."""
    try:
        # Parse request data
        data = await request.json()
        email = data.get("email")
        password = data.get("password")

        # Validate inputs
        if not email or not password:
            logger.warning("Login attempt with missing email or password")
            return {"status": 400, "message": "Email and password are required"}

        # Initialize configuration and database connection
        config = get_app_config()
        try:
            cosmos_db = get_cosmos_db_cached(config)
            logger.debug("CosmosDB client initialized for login")
        except DatabaseError as e:
            logger.error(f"Database initialization failed: {str(e)}")
            return {"status": 503, "message": "Database service unavailable"}

        # Authenticate user
        try:
            user = await authenticate_user(cosmos_db, email, password)
            if not user:
                logger.warning(f"Failed login attempt for email: {email}")
                return {"status": 401, "message": "Incorrect email or password"}

            # Generate access token
            access_token = create_access_token(
                data={"sub": user["email"]}, config=config
            )
            
            # Track login analytics
            try:
                analytics_service = AnalyticsService(cosmos_db)
                await analytics_service.track_user_session(
                    user_id=user["id"],
                    action="login",
                    metadata={
                        "email": user["email"],
                        "login_method": "password",
                        "permission": user.get("permission", "Unknown")
                    }
                )
                await analytics_service.track_event(
                    event_type="user_login",
                    user_id=user["id"],
                    metadata={
                        "email": user["email"],
                        "login_method": "password",
                        "permission": user.get("permission", "Unknown")
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to track login analytics: {str(e)}")
            
            logger.info(f"Successful login for user: {email}")
            return {
                "status": 200,
                "message": "Login successful",
                "access_token": access_token,
                "token_type": "bearer",
            }
        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}", exc_info=True)
            return {"status": 500, "message": f"Authentication error: {str(e)}"}

    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}", exc_info=True)
        return {"status": 500, "message": f"An unexpected error occurred: {str(e)}"}


@router.post("/microsoft-sso")
async def microsoft_sso_auth(request: Request):
    """Authenticate or register a user using Microsoft SSO login response."""
    try:
        data = await request.json()
        id_token = data.get("id_token")
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        
        # Extract user info from tokens
        email = None
        full_name = None
        given_name = None
        family_name = None
        oid = None
        tenant_id = None

        # Prefer id_token for user info (OpenID Connect standard)
        if id_token:
            try:
                decoded = jwt.get_unverified_claims(id_token)
                email = decoded.get("email") or decoded.get("upn") or decoded.get("preferred_username")
                full_name = decoded.get("name")
                given_name = decoded.get("given_name")
                family_name = decoded.get("family_name")
                oid = decoded.get("oid")
                tenant_id = decoded.get("tid")
            except Exception as e:
                return {"message": f"Invalid id_token: {str(e)}", "status": 400}
        elif access_token:
            try:
                decoded = jwt.get_unverified_claims(access_token)
                email = decoded.get("email") or decoded.get("upn") or decoded.get("preferred_username")
                full_name = decoded.get("name")
                given_name = decoded.get("given_name")
                family_name = decoded.get("family_name")
                oid = decoded.get("oid")
                tenant_id = decoded.get("tid")
            except Exception as e:
                return {"message": f"Invalid access_token: {str(e)}", "status": 400}
        else:
            return {"message": "Missing id_token or access_token", "status": 400}

        if not email:
            return {"message": "No email found in token", "status": 400}

        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)

        # Try to find user by email or create new one
        user = await cosmos_db.get_user_by_email(email)
        if not user:
            # Register new user
            from ...models.permissions import PermissionLevel
            user_data = {
                "id": str(uuid.uuid4()),
                "email": email,
                "password": None,
                "permission": PermissionLevel.USER.value,
                "source": "microsoft",
                "full_name": full_name,
                "given_name": given_name,
                "family_name": family_name,
                "microsoft_oid": oid,
                "tenant_id": tenant_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_login": datetime.now(timezone.utc).isoformat(),
                "is_active": True,
                "refresh_token": refresh_token,
            }
            user = await cosmos_db.create_user(user_data)
        else:
            # Update existing user
            update_data = {
                "last_login": datetime.now(timezone.utc).isoformat(),
                "full_name": full_name,
                "given_name": given_name,
                "family_name": family_name,
                "microsoft_oid": oid,
                "tenant_id": tenant_id,
                "is_active": True,
                "refresh_token": refresh_token,
            }
            user = await cosmos_db.update_user(user["id"], update_data)

        # Generate app access token
        app_access_token = create_access_token(data={"sub": email}, config=config)
        
        # Track Microsoft SSO login analytics
        try:
            analytics_service = AnalyticsService(cosmos_db)
            await analytics_service.track_user_session(
                user_id=user["id"],
                action="login",
                metadata={
                    "email": user["email"],
                    "login_method": "microsoft_sso",
                    "permission": user.get("permission", "User"),
                    "tenant_id": tenant_id,
                    "full_name": full_name
                }
            )
            await analytics_service.track_event(
                event_type="user_login",
                user_id=user["id"],
                metadata={
                    "email": user["email"],
                    "login_method": "microsoft_sso",
                    "permission": user.get("permission", "User"),
                    "tenant_id": tenant_id,
                    "full_name": full_name
                }
            )
        except Exception as e:
            logger.warning(f"Failed to track Microsoft SSO login analytics: {str(e)}")
        
        return {
            "status": 200,
            "message": "Microsoft SSO login successful",
            "access_token": app_access_token,
            "token_type": "bearer",
            "permission": user.get("permission", "User"),
            "user": {
                "email": user["email"],
                "full_name": user.get("full_name"),
                "permission": user.get("permission", "User")
            }
        }
    except Exception as e:
        return {"message": f"Unexpected error: {str(e)}", "status": 500}
