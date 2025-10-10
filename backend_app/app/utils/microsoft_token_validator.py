"""
Microsoft Azure AD Token Validator

This module provides secure token validation for Microsoft Azure AD / Entra ID tokens.
It validates:
- Token signature using Microsoft's public keys (JWKS)
- Token issuer (must be from Microsoft)
- Token audience (must match your app's client ID)
- Token expiration
- Tenant ID (must match your configured tenant)
"""

import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import jwt
from jwt import PyJWKClient
from jwt.exceptions import (
    InvalidTokenError,
    ExpiredSignatureError,
    InvalidAudienceError,
    InvalidIssuerError,
)

logger = logging.getLogger(__name__)


class MicrosoftTokenValidator:
    """
    Validates Microsoft Azure AD / Entra ID tokens with proper signature verification.
    
    Uses Microsoft's JWKS (JSON Web Key Set) endpoint to fetch public keys and
    verify token signatures. Keys are cached for performance.
    """
    
    # Microsoft's JWKS endpoint for token validation
    # This endpoint provides the public keys used to verify JWT signatures
    JWKS_URI = "https://login.microsoftonline.com/common/discovery/v2.0/keys"
    
    def __init__(
        self,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        jwks_cache_ttl: int = 3600,  # Cache keys for 1 hour
    ):
        """
        Initialize the Microsoft token validator.
        
        Args:
            tenant_id: Your Azure AD tenant ID (GUID). If provided, will validate
                      that tokens are issued by this specific tenant.
            client_id: Your application's client ID. If provided, will validate
                      that tokens are intended for your application (audience check).
            jwks_cache_ttl: How long to cache JWKS keys in seconds (default 1 hour)
        """
        self.tenant_id = tenant_id
        self.client_id = client_id
        
        # Initialize PyJWKClient for fetching and caching Microsoft's public keys
        self.jwks_client = PyJWKClient(
            self.JWKS_URI,
            cache_keys=True,
            max_cached_keys=16,
            cache_jwk_set=True,
            lifespan=jwks_cache_ttl,
        )
        
        logger.info(
            "Initialized Microsoft token validator",
            extra={
                "tenant_validation": "enabled" if tenant_id else "disabled",
                "audience_validation": "enabled" if client_id else "disabled",
            }
        )
    
    def validate_token(self, token: str, validate_tenant: bool = True) -> Dict[str, Any]:
        """
        Validate a Microsoft Azure AD token with full signature verification.
        
        Args:
            token: The JWT token string to validate
            validate_tenant: If True and tenant_id is configured, validate that
                           the token is from the expected tenant
        
        Returns:
            Dict containing the validated token claims/payload
            
        Raises:
            InvalidTokenError: If token validation fails for any reason
            ExpiredSignatureError: If token has expired
            InvalidAudienceError: If audience doesn't match expected client_id
            InvalidIssuerError: If issuer is not Microsoft or wrong tenant
        """
        try:
            # Get the signing key from the JWT header
            # This fetches the public key from Microsoft's JWKS endpoint
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            
            # Build validation options
            options = {
                "verify_signature": True,
                "verify_exp": True,
                "verify_nbf": True,  # Not before
                "verify_iat": True,  # Issued at
                "require_exp": True,
                "require_iat": True,
            }
            
            # Prepare expected issuer patterns
            # Microsoft tokens can be issued by various issuers depending on version
            expected_issuers = []
            if self.tenant_id:
                # V2.0 endpoint issuer
                expected_issuers.append(f"https://login.microsoftonline.com/{self.tenant_id}/v2.0")
                # V1.0 endpoint issuer
                expected_issuers.append(f"https://sts.windows.net/{self.tenant_id}/")
            else:
                # If no specific tenant, at least verify it's from Microsoft
                # We'll do a manual check below
                pass
            
            # Decode and validate the token
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],  # Microsoft uses RS256
                audience=self.client_id if self.client_id else None,
                issuer=expected_issuers[0] if expected_issuers else None,
                options=options,
            )
            
            # Additional validation: Check issuer is from Microsoft if no specific tenant
            if not self.tenant_id:
                issuer = payload.get("iss", "")
                if not (
                    issuer.startswith("https://login.microsoftonline.com/")
                    or issuer.startswith("https://sts.windows.net/")
                ):
                    raise InvalidIssuerError(
                        f"Token issuer is not from Microsoft: {issuer}"
                    )
            
            # Additional validation: Check tenant ID matches if required
            if validate_tenant and self.tenant_id:
                token_tenant = payload.get("tid")
                if token_tenant != self.tenant_id:
                    raise InvalidTokenError(
                        f"Token tenant '{token_tenant}' does not match expected tenant '{self.tenant_id}'"
                    )
            
            # Log successful validation
            logger.info(
                "Token validated successfully",
                extra={
                    "tenant_id": payload.get("tid"),
                    "user": payload.get("preferred_username") or payload.get("email"),
                    "expires": datetime.fromtimestamp(payload.get("exp", 0), tz=timezone.utc).isoformat(),
                }
            )
            
            return payload
            
        except ExpiredSignatureError as e:
            logger.warning("Token validation failed: Token has expired")
            raise
        except InvalidAudienceError as e:
            logger.warning(
                "Token validation failed: Invalid audience",
                extra={"expected": self.client_id}
            )
            raise
        except InvalidIssuerError as e:
            logger.warning("Token validation failed: Invalid issuer")
            raise
        except InvalidTokenError as e:
            logger.warning(f"Token validation failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error during token validation: {str(e)}",
                exc_info=True
            )
            raise InvalidTokenError(f"Token validation failed: {str(e)}") from e
    
    def get_unvalidated_claims(self, token: str) -> Dict[str, Any]:
        """
        Get claims from token WITHOUT validation (use with caution!).
        
        This should ONLY be used for debugging or logging purposes.
        Never trust these claims for authentication/authorization decisions.
        
        Args:
            token: The JWT token string
            
        Returns:
            Dict containing the token claims (unverified)
        """
        logger.warning("Getting unvalidated token claims - DO NOT use for auth decisions")
        return jwt.decode(token, options={"verify_signature": False})
    
    def validate_id_token(self, id_token: str) -> Dict[str, Any]:
        """
        Validate an OpenID Connect ID token from Microsoft.
        
        ID tokens contain user identity information and should be validated
        before extracting user details.
        
        Args:
            id_token: The ID token JWT string
            
        Returns:
            Dict containing validated user claims
        """
        return self.validate_token(id_token, validate_tenant=True)
    
    def validate_access_token(self, access_token: str) -> Dict[str, Any]:
        """
        Validate a Microsoft access token.
        
        Note: Access tokens are typically opaque and not always JWTs.
        This method works only if the access token is a JWT.
        
        Args:
            access_token: The access token string
            
        Returns:
            Dict containing validated token claims
        """
        return self.validate_token(access_token, validate_tenant=True)
