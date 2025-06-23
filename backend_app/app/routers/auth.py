from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Request, Body, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from azure.cosmos.exceptions import CosmosHttpResponseError
import logging
import traceback
from fastapi import Request
from fastapi.responses import JSONResponse
import uuid
from app.core.config import AppConfig, CosmosDB, DatabaseError
from app.middleware.permission_middleware import (
    PermissionLevel, 
    PermissionChecker,
    require_admin_user,
    require_user_user
)
from app.utils.permission_queries import PermissionQueryOptimizer

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: str | None = None


class UserBase(BaseModel):
    email: str


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: str
    created_at: str
    updated_at: str


class ChangePasswordRequest(BaseModel):
    new_password: str


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, config: AppConfig) -> str:
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

    config = AppConfig()
    cosmos_db = CosmosDB(config)

    try:
        payload = jwt.decode(
            token,
            config.auth["jwt_secret_key"],
            algorithms=[config.auth["jwt_algorithm"]],
        )
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception

    try:
        # Await the async call to `get_user_by_email`
        user = await cosmos_db.get_user_by_email(email=token_data.email)
        if user is None:
            raise credentials_exception
        return user
    except Exception as e:
        raise credentials_exception


async def authenticate_user(
    cosmos_db: CosmosDB, email: str, password: str
) -> Dict[str, Any] | bool:
    """Authenticate user credentials."""
    user = await cosmos_db.get_user_by_email(email)  # Await the async method
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
        config = AppConfig()
        try:
            cosmos_db = CosmosDB(config)
            logger.debug("CosmosDB client initialized for login")
        except DatabaseError as e:
            logger.error(f"Database initialization failed: {str(e)}")
            return {"status": 503, "message": "Database service unavailable"}

        # Authenticate user
        try:
            user = await authenticate_user(cosmos_db, email, password)  # Await here
            if not user:
                logger.warning(f"Failed login attempt for email: {email}")
                return {"status": 401, "message": "Incorrect email or password"}

            # Generate access token
            access_token = create_access_token(
                data={"sub": user["email"]}, config=config
            )
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

@router.get("/users")
async def get_all_users():
    try:
        config = AppConfig()
        cosmos_db = CosmosDB(config)
        users = await cosmos_db.get_all_users()
        for user in users:
            user.pop("hashed_password", None)
        return {"status": 200, "users": users}
    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}", exc_info=True)
        return {"status": 500, "message": f"Error fetching users: {str(e)}"}

@router.patch("/users/{user_id}")
async def update_user_permission(user_id: str, update_data: dict = Body(...)):
    try:
        config = AppConfig()
        cosmos_db = CosmosDB(config)
        updated_user = await cosmos_db.update_user(user_id, update_data)
        # Remove sensitive info if present
        updated_user.pop("hashed_password", None)
        return {"status": 200, "user": updated_user}
    except ValueError as e:
        logger.error(f"User not found: {str(e)}", exc_info=True)
        return {"status": 404, "message": str(e)}
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}", exc_info=True)
        return {"status": 500, "message": f"Error updating user: {str(e)}"}
        from fastapi import Query

@router.get("/users/by-email")
async def get_user_by_email(email: str = Query(..., description="User's email address")):
    try:
        config = AppConfig()
        cosmos_db = CosmosDB(config)
        user = await cosmos_db.get_user_by_email(email)
        if not user:
            return {"status": 404, "message": f"User with email {email} not found"}
        user.pop("hashed_password", None)
        return {"status": 200, "user": user}
    except Exception as e:
        logger.error(f"Error fetching user by email: {str(e)}", exc_info=True)
        return {"status": 500, "message": f"Error fetching user: {str(e)}"}

        
@router.post("/register")
async def register_user(request: Request, current_user: Dict[str, Any] = Depends(require_admin_user)):
    try:
        data = await request.json()
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            logger.warning("Registration attempt with missing email or password")
            return {"status": 400, "message": "Email and password are required"}

        config = AppConfig()
        try:
            cosmos_db = CosmosDB(config)
            logger.debug("CosmosDB client initialized")
        except DatabaseError as e:
            logger.error(f"Database initialization failed: {str(e)}")
            return {"status": 503, "message": "Database service unavailable"}

        # Check if user already exists
        try:
            existing_user = await cosmos_db.get_user_by_email(email)  # Use await here
            if existing_user:
                logger.warning(f"Registration attempt for existing email: {email}")
                return {"status": 400, "message": "Email already registered"}
        except ValueError as e:
            logger.error(f"Error checking existing user: {str(e)}", exc_info=True)
            return {
                "status": 500,
                "message": f"Error checking user existence: {str(e)}",
            }

        # Create new user document
        timestamp = int(
            datetime.now(timezone.utc).timestamp() * 1000
        )  # milliseconds since epoch
        user_data = {
            "id": f"user_{timestamp}",
            "type": "user",
            "email": email,
            "hashed_password": get_password_hash(password),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        logger.debug(f"Attempting to create user with data: {user_data}")

        try:
            created_user = await cosmos_db.create_user(user_data)  # Use await here
            logger.info(f"User successfully created with ID: {created_user['id']}")
            return {"status": 200, "message": f"User {email} created successfully"}
        except ValueError as e:
            logger.error(f"Error creating user: {str(e)}", exc_info=True)
            return {"status": 500, "message": f"Error creating user: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error creating user: {str(e)}", exc_info=True)
            return {
                "status": 500,
                "message": f"Unexpected error creating user: {str(e)}",
            }

    except Exception as e:
        logger.error(f"Unexpected error during registration: {str(e)}", exc_info=True)
        return {"status": 500, "message": f"An unexpected error occurred: {str(e)}"}

# ENHANCED PERMISSION ENDPOINTS

@router.get("/users/by-permission/{permission_level}")
async def get_users_by_permission(
    permission_level: str,
    limit: int = Query(default=100, le=1000),
    current_user: Dict[str, Any] = Depends(require_admin_user)
):
    """
    Get users by permission level. Admin only.
    """
    try:
        cosmos_db = CosmosDB()
        optimizer = PermissionQueryOptimizer(
            cosmos_db.client, 
            cosmos_db.database_name, 
            cosmos_db.container_name
        )
        
        users = await optimizer.get_users_by_permission(permission_level, limit)
        return {
            "status": 200,
            "data": users,
            "count": len(users),
            "permission_level": permission_level
        }
    except Exception as e:
        logger.error(f"Error fetching users by permission: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching users: {str(e)}"
        )

@router.get("/users/permission-stats")
async def get_permission_statistics(
    current_user: Dict[str, Any] = Depends(require_admin_user)
):
    """
    Get permission distribution statistics. Admin only.
    """
    try:
        cosmos_db = CosmosDB()
        optimizer = PermissionQueryOptimizer(
            cosmos_db.client, 
            cosmos_db.database_name, 
            cosmos_db.container_name
        )
        
        stats = await optimizer.get_permission_counts()
        total_users = sum(stats.values())
        
        # Calculate percentages
        percentages = {
            perm: round((count / total_users) * 100, 2) if total_users > 0 else 0
            for perm, count in stats.items()
        }
        
        return {
            "status": 200,
            "data": {
                "counts": stats,
                "percentages": percentages,
                "total_users": total_users
            }
        }
    except Exception as e:
        logger.error(f"Error fetching permission stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching statistics: {str(e)}"
        )

@router.patch("/users/{user_id}/permission")
async def update_user_permission(
    user_id: str,
    permission_data: Dict[str, str] = Body(...),
    current_user: Dict[str, Any] = Depends(require_admin_user)
):
    """
    Update user permission level. Admin only.
    Includes audit trail tracking.
    """
    try:
        new_permission = permission_data.get("permission")
        if new_permission not in [PermissionLevel.ADMIN, PermissionLevel.USER, PermissionLevel.VIEWER]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid permission level. Must be one of: {[PermissionLevel.ADMIN, PermissionLevel.USER, PermissionLevel.VIEWER]}"
            )
        
        cosmos_db = CosmosDB()
        
        # Get current user data
        current_user_data = await cosmos_db.get_user_by_id(user_id)
        if not current_user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        old_permission = current_user_data.get("permission", PermissionLevel.VIEWER)
        
        # Prepare update data with audit trail
        update_data = {
            "permission": new_permission,
            "permission_changed_at": datetime.now(timezone.utc).isoformat(),
            "permission_changed_by": current_user.get("email", "unknown"),
            "permission_history": current_user_data.get("permission_history", [])
        }
        
        # Add to permission history
        update_data["permission_history"].append({
            "old_permission": old_permission,
            "new_permission": new_permission,
            "changed_at": update_data["permission_changed_at"],
            "changed_by": update_data["permission_changed_by"]
        })
        
        # Update user
        updated_user = await cosmos_db.update_user(user_id, update_data)
        
        # Clear permission cache
        optimizer = PermissionQueryOptimizer(
            cosmos_db.client, 
            cosmos_db.database_name, 
            cosmos_db.container_name
        )
        optimizer.clear_permission_cache(user_id)
        
        logger.info(f"Permission updated for user {user_id}: {old_permission} -> {new_permission} by {current_user.get('email')}")
        
        return {
            "status": 200,
            "message": f"Permission updated successfully from {old_permission} to {new_permission}",
            "data": {
                "user_id": user_id,
                "old_permission": old_permission,
                "new_permission": new_permission,
                "updated_at": update_data["permission_changed_at"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user permission: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating permission: {str(e)}"
        )

@router.get("/users/elevated-permissions/{base_permission}")
async def get_users_with_elevated_permissions(
    base_permission: str,
    current_user: Dict[str, Any] = Depends(require_admin_user)
):
    """
    Get users with permissions higher than the specified base permission. Admin only.
    """
    try:
        cosmos_db = CosmosDB()
        optimizer = PermissionQueryOptimizer(
            cosmos_db.client, 
            cosmos_db.database_name, 
            cosmos_db.container_name
        )
        
        users = await optimizer.get_users_with_elevated_permissions(base_permission)
        
        return {
            "status": 200,
            "data": users,
            "count": len(users),
            "base_permission": base_permission
        }
    except Exception as e:
        logger.error(f"Error fetching users with elevated permissions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching users: {str(e)}"
        )

@router.get("/permissions/audit")
async def get_permission_audit_trail(
    days_back: int = Query(default=30, le=365),
    current_user: Dict[str, Any] = Depends(require_admin_user)
):
    """
    Get recent permission changes for audit purposes. Admin only.
    """
    try:
        cosmos_db = CosmosDB()
        optimizer = PermissionQueryOptimizer(
            cosmos_db.client, 
            cosmos_db.database_name, 
            cosmos_db.container_name
        )
        
        audit_data = await optimizer.audit_permission_changes(days_back)
        
        return {
            "status": 200,
            "data": audit_data,
            "count": len(audit_data),
            "days_back": days_back
        }
    except Exception as e:
        logger.error(f"Error fetching permission audit trail: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching audit trail: {str(e)}"
        )

@router.get("/users/me/permissions")
async def get_my_permissions(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get current user's permission information.
    """
    try:
        permission = current_user.get("permission", PermissionLevel.VIEWER)
          # Get permission capabilities using the utility function
        from app.middleware.permission_middleware import get_user_capabilities
        capabilities = get_user_capabilities(permission)
        
        return {
            "status": 200,
            "data": {
                "user_id": current_user.get("id"),
                "email": current_user.get("email"),
                "permission": permission,
                "capabilities": capabilities
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching user permissions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching permissions: {str(e)}"
        )

@router.get("/permissions/cache-stats")
async def get_permission_cache_stats(
    current_user: Dict[str, Any] = Depends(require_admin_user)
):
    """
    Get permission cache statistics. Admin only.
    """
    try:
        cosmos_db = CosmosDB()
        optimizer = PermissionQueryOptimizer(
            cosmos_db.client, 
            cosmos_db.database_name, 
            cosmos_db.container_name
        )
        
        cache_stats = optimizer.get_cache_stats()
        
        return {
            "status": 200,
            "data": cache_stats
        }
    except Exception as e:
        logger.error(f"Error fetching cache stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching cache stats: {str(e)}"
        )

@router.patch("/users/{user_id}/password")
async def change_user_password(
    user_id: str,
    password_data: ChangePasswordRequest = Body(...),
    current_user: Dict[str, Any] = Depends(require_admin_user)
):
    """
    Change user password. Admin only.
    """
    try:
        config = AppConfig()
        cosmos_db = CosmosDB(config)
        
        # Get current user data to verify user exists
        user_to_update = await cosmos_db.get_user_by_id(user_id)
        if not user_to_update:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Hash the new password
        hashed_password = get_password_hash(password_data.new_password)
        
        # Prepare update data
        update_data = {
            "hashed_password": hashed_password,
            "password_changed_at": datetime.now(timezone.utc).isoformat(),
            "password_changed_by": current_user.get("email", "unknown")
        }
        
        # Update user password
        updated_user = await cosmos_db.update_user(user_id, update_data)
        
        # Remove sensitive information from response
        updated_user.pop("hashed_password", None)
        
        logger.info(f"Password changed for user {user_id} by {current_user.get('email')}")
        
        return {
            "status": 200,
            "message": "Password changed successfully",
            "data": {
                "user_id": user_id,
                "email": updated_user.get("email"),
                "updated_at": update_data["password_changed_at"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing password for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error changing password: {str(e)}"
        )

@router.post("/microsoft-sso")
async def microsoft_sso_auth(request: Request):
    """
    Authenticate or register a user using Microsoft SSO login response.
    Accepts the full Microsoft login response object.
    """
    try:
        data = await request.json()
        # Accept the full Microsoft login response
        id_token = data.get("id_token")
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        email = None
        full_name = None
        given_name = None
        family_name = None
        oid = None
        tenant_id = None
        decoded = None

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
                return JSONResponse(status_code=400, content={"message": f"Invalid id_token: {str(e)}"})
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
                return JSONResponse(status_code=400, content={"message": f"Invalid access_token: {str(e)}"})
        else:
            return JSONResponse(status_code=400, content={"message": "Missing id_token or access_token"})

        if not email:
            return JSONResponse(status_code=400, content={"message": "No email found in token"})

        config = AppConfig()
        cosmos_db = CosmosDB(config)

        # Try to find user by email
        user = await cosmos_db.get_user_by_email(email)
        if not user:
            # Register new user
            user_data = {
                "id": str(uuid.uuid4()),
                "email": email,
                "password": None,
                "permission": "user",
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
            # Update last_login and any new info
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
        return {
            "status": 200,
            "message": "Microsoft SSO login successful",
            "access_token": app_access_token,
            "token_type": "bearer",
            "permission": user.get("permission", "user"),
            "user": {
                "email": user["email"],
                "full_name": user.get("full_name"),
                "permission": user.get("permission", "user")
            }
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"Unexpected error: {str(e)}"})
