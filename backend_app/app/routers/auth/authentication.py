"""
Authentication Router - Core authentication operations
Handles login, logout, and token management
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError, InvalidAudienceError, InvalidIssuerError
from passlib.context import CryptContext
from pydantic import BaseModel
import logging
import uuid

from ...core.dependencies import (
    CosmosService,
    get_cosmos_service,
    get_analytics_service,
    get_error_handler,
)
from ...core.config import get_config
from ...core.errors import (
    ApplicationError,
    ErrorCode,
    AuthenticationError,
    ErrorHandler,
    ValidationError,
)
from ...utils.microsoft_token_validator import MicrosoftTokenValidator

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(prefix="", tags=["authentication"])

def _handle_internal_error(
    error_handler: ErrorHandler,
    action: str,
    exc: Exception,
    *,
    error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
    status_code: int = 500,
    message: str | None = None,
    details: dict | None = None,
) -> None:
    error_handler.raise_internal(
        action,
        exc,
        message=message,
        error_code=error_code,
        status_code=status_code,
        extra=details,
    )
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


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    cosmos_service: CosmosService = Depends(get_cosmos_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
) -> Dict[str, Any]:
    # use module-level _handle_internal_error
    try:
        config = get_config()
    except Exception as exc:
        _handle_internal_error(error_handler, "load authentication configuration", exc)

    try:
        logger.debug("Attempting to decode JWT token")
        payload = jwt.decode(
            token,
            config.jwt_secret_key,
            algorithms=[config.jwt_algorithm],
        )
        email: Optional[str] = payload.get("sub")
        if not email:
            logger.error("No email found in JWT payload")
            raise AuthenticationError(
                "Could not validate credentials",
                details={"reason": "missing_subject", "auth_scheme": "Bearer"},
            )
        logger.debug("JWT decoded successfully for email: %s", email)
    except JWTError as exc:
        logger.error("JWT decode error: %s", str(exc))
        raise AuthenticationError(
            "Could not validate credentials",
            details={"reason": "invalid_token", "auth_scheme": "Bearer"},
        ) from exc

    try:
        logger.debug("Looking up user by email: %s", email)
        user = await cosmos_service.get_user_by_email(email=email)
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "lookup user for authentication",
            exc,
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            details={"email": email},
        )

    if user is None:
        logger.error("User not found in database: %s", email)
        raise AuthenticationError(
            "Could not validate credentials",
            details={"reason": "user_not_found", "email": email},
        )

    logger.debug("User found successfully: %s", user.get("id", "unknown"))
    return user


async def authenticate_user(
    cosmos_service: CosmosService,
    email: str,
    password: str,
    *,
    error_handler: ErrorHandler,
) -> Dict[str, Any] | bool:
    """Authenticate user credentials."""
    try:
        user = await cosmos_service.get_user_by_email(email)
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "retrieve user for authentication",
            exc,
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            details={"email": email},
        )
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return user


@router.post("/login")
async def login_for_access_token(
    request: Request,
    cosmos_service: CosmosService = Depends(get_cosmos_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    """Handle user login and token generation."""
    email: Optional[str] = None
    try:
        data = await request.json()
        email = data.get("email")
        password = data.get("password")

        missing_fields = [
            field for field, value in {"email": email, "password": password}.items() if not value
        ]
        if missing_fields:
            logger.warning("Login attempt with missing credentials: %s", missing_fields)
            raise ValidationError(
                "Email and password are required",
                details={"missing_fields": missing_fields},
            )

        try:
            config = get_config()
            logger.debug("Configuration loaded for login")
        except Exception as exc:
            _handle_internal_error(error_handler, "load authentication configuration", exc)

        try:
            user = await authenticate_user(
                cosmos_service,
                email,
                password,
                error_handler=error_handler,
            )
        except ApplicationError:
            raise
        except Exception as exc:
            _handle_internal_error(
                error_handler,
                "authenticate user credentials",
                exc,
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                details={"email": email},
            )

        if not user:
            logger.warning("Failed login attempt for email: %s", email)
            raise AuthenticationError(
                "Incorrect email or password",
                details={"email": email},
            )

        try:
            access_token = create_access_token(
                data={"sub": user["email"]},
                config=config,
            )
        except Exception as exc:
            _handle_internal_error(
                error_handler,
                "create access token",
                exc,
                details={"email": email},
            )

        logger.info("Successful login for user: %s", email)
        return {
            "status": 200,
            "message": "Login successful",
            "access_token": access_token,
            "token_type": "bearer",
        }

    except ApplicationError:
        raise
    except Exception as exc:
        details = {"email": email} if email else None
        _handle_internal_error(error_handler, "process login request", exc, details=details)


@router.post("/microsoft-sso")
async def microsoft_sso_auth(
    request: Request,
    cosmos_service: CosmosService = Depends(get_cosmos_service),
    analytics_service = Depends(get_analytics_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    """Authenticate or register a user using Microsoft SSO login response."""
    email: Optional[str] = None
    try:
        data = await request.json()
        id_token = data.get("id_token")
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")

        # Get configuration for token validation
        try:
            config = get_config()
        except Exception as exc:
            _handle_internal_error(error_handler, "load authentication configuration", exc)

        # Initialize Microsoft token validator with tenant and client ID validation
        validator = MicrosoftTokenValidator(
            tenant_id=config.microsoft_tenant_id,
            client_id=config.microsoft_client_id,
        )

        # Extract user info from tokens with PROPER VALIDATION
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
                # SECURE: Validate token signature, issuer, audience, expiration
                decoded = validator.validate_id_token(id_token)
                logger.info("ID token validated successfully")
            except ExpiredSignatureError:
                raise ValidationError(
                    "ID token has expired",
                    details={"reason": "Token expired"},
                )
            except InvalidAudienceError:
                raise ValidationError(
                    "ID token audience mismatch - token not intended for this application",
                    details={"reason": "Invalid audience"},
                )
            except InvalidIssuerError:
                raise ValidationError(
                    "ID token from untrusted issuer",
                    details={"reason": "Invalid issuer"},
                )
            except InvalidTokenError as exc:
                raise ValidationError(
                    "Invalid ID token",
                    details={"reason": str(exc)},
                ) from exc
        elif access_token:
            try:
                # SECURE: Validate access token
                decoded = validator.validate_access_token(access_token)
                logger.info("Access token validated successfully")
            except ExpiredSignatureError:
                raise ValidationError(
                    "Access token has expired",
                    details={"reason": "Token expired"},
                )
            except InvalidAudienceError:
                raise ValidationError(
                    "Access token audience mismatch - token not intended for this application",
                    details={"reason": "Invalid audience"},
                )
            except InvalidIssuerError:
                raise ValidationError(
                    "Access token from untrusted issuer",
                    details={"reason": "Invalid issuer"},
                )
            except InvalidTokenError as exc:
                raise ValidationError(
                    "Invalid access token",
                    details={"reason": str(exc)},
                ) from exc
        else:
            raise ValidationError("Missing id_token or access_token")

        # Extract user information from validated token
        email = (
            decoded.get("email")
            or decoded.get("upn")
            or decoded.get("preferred_username")
        )
        full_name = decoded.get("name")
        given_name = decoded.get("given_name")
        family_name = decoded.get("family_name")
        oid = decoded.get("oid")
        tenant_id = decoded.get("tid")

        # SECURITY: Validate tenant ID matches configuration
        if config.microsoft_tenant_id and tenant_id != config.microsoft_tenant_id:
            logger.error(
                f"Tenant ID mismatch: token from tenant {tenant_id}, expected {config.microsoft_tenant_id}"
            )
            raise AuthenticationError(
                "Authentication failed: Invalid tenant",
                details={"reason": "Tenant not authorized"},
            )

        if not email:
            raise ValidationError(
                "No email found in token",
                details={"token_type": "id_token" if id_token else "access_token"},
            )

        try:
            config = get_config()
        except Exception as exc:
            _handle_internal_error(error_handler, "load authentication configuration", exc)

        try:
            user = await cosmos_service.get_user_by_email(email)
        except ApplicationError:
            raise
        except Exception as exc:
            _handle_internal_error(
                error_handler,
                "lookup user for microsoft sso",
                exc,
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                details={"email": email},
            )

        if not user:
            from ...models.permissions import PermissionLevel

            user_data = {
                "id": str(uuid.uuid4()),
                "type": "user",
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
            try:
                user = await cosmos_service.create_user(user_data)
            except ApplicationError:
                raise
            except Exception as exc:
                _handle_internal_error(
                    error_handler,
                    "create microsoft sso user",
                    exc,
                    error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                    details={"email": email},
                )
        else:
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
            try:
                user = await cosmos_service.update_user(user["id"], update_data)
            except ApplicationError:
                raise
            except Exception as exc:
                _handle_internal_error(
                    error_handler,
                    "update microsoft sso user",
                    exc,
                    error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                    details={"email": email, "user_id": user.get("id")},
                )

        try:
            app_access_token = create_access_token(data={"sub": email}, config=config)
        except Exception as exc:
            _handle_internal_error(
                error_handler,
                "create app access token",
                exc,
                details={"email": email},
            )

        try:
            await analytics_service.track_event(
                event_type="user_login",
                user_id=user["id"],
                metadata={
                    "email": user["email"],
                    "login_method": "microsoft_sso",
                    "permission": user.get("permission", "User"),
                    "tenant_id": tenant_id,
                    "full_name": full_name,
                },
            )
        except Exception as exc:
            logger.warning(
                "Failed to track Microsoft SSO login analytics: %s",
                str(exc),
            )

        return {
            "status": 200,
            "message": "Microsoft SSO login successful",
            "access_token": app_access_token,
            "token_type": "bearer",
            "permission": user.get("permission", "User"),
            "user": {
                "email": user["email"],
                "full_name": user.get("full_name"),
                "permission": user.get("permission", "User"),
            },
        }

    except ApplicationError:
        raise
    except Exception as exc:
        details = {"email": email} if email else None
        _handle_internal_error(error_handler, "process microsoft sso authentication", exc, details=details)
