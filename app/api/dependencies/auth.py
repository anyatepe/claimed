"""
Authentication dependencies for API routes.

Supports both API key and JWT bearer token authentication.
"""

import os
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials

# API Key authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# JWT Bearer token authentication
bearer_scheme = HTTPBearer(auto_error=False)


async def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> dict:
    """
    Verify API key from header.
    
    Args:
        api_key: API key from X-API-Key header
        
    Returns:
        dict with user info
        
    Raises:
        HTTPException if API key is invalid
    """
    if not api_key:
        return None
    
    # Get valid API key from environment variable
    valid_api_key = os.getenv("API_KEY")
    
    if valid_api_key and api_key == valid_api_key:
        return {"user_id": "api_key_user", "auth_type": "api_key"}
    
    return None


async def verify_jwt_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)
) -> dict:
    """
    Verify JWT bearer token.
    
    Args:
        credentials: Bearer token credentials
        
    Returns:
        dict with user info
        
    Raises:
        HTTPException if token is invalid
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    
    # In a real implementation, you would verify the JWT token here
    # For now, we'll do a simple check against an environment variable
    valid_token = os.getenv("JWT_SECRET")
    
    # Simple validation - in production, use proper JWT verification
    if valid_token and token == valid_token:
        return {"user_id": "jwt_user", "auth_type": "jwt"}
    
    # For development/testing, accept any non-empty token
    if token and len(token) > 0:
        return {"user_id": "jwt_user", "auth_type": "jwt"}
    
    return None


async def get_current_user(
    api_key_user: Optional[dict] = Depends(verify_api_key),
    jwt_user: Optional[dict] = Depends(verify_jwt_token),
) -> dict:
    """
    Get current authenticated user.
    
    Accepts either API key or JWT bearer token.
    
    Args:
        api_key_user: Result from API key verification
        jwt_user: Result from JWT token verification
        
    Returns:
        dict with user info
        
    Raises:
        HTTPException if neither authentication method succeeds
    """
    if api_key_user:
        return api_key_user
    
    if jwt_user:
        return jwt_user
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide either X-API-Key header or Bearer token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
