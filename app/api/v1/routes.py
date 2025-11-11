"""
Example v1 API routes protected by authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from app.utils.auth import AuthUser, get_current_user, require_tenant

router = APIRouter(prefix="/v1", tags=["v1"])


@router.get("/health")
async def health_check():
    """Public health check endpoint (not protected)."""
    return {"status": "ok"}


@router.get("/protected")
async def protected_endpoint(user: AuthUser = Depends(get_current_user)):
    """Protected endpoint requiring authentication."""
    return {
        "message": "This is a protected endpoint",
        "user": {
            "api_key": user.api_key[:8] + "..." if user.api_key else None,
            "tenant": user.tenant,
            "user_id": user.user_id
        }
    }


@router.get("/tenant/{tenant_name}")
async def tenant_scoped_endpoint(
    tenant_name: str,
    user: AuthUser = Depends(get_current_user)
):
    """Endpoint that checks tenant scoping."""
    if user.tenant != tenant_name:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Required tenant: {tenant_name}, user tenant: {user.tenant}"
        )
    
    return {
        "message": f"Access granted for tenant: {tenant_name}",
        "tenant": user.tenant
    }


@router.get("/tenant-scoped/{tenant_name}")
async def tenant_scoped_with_dependency(
    tenant_name: str,
    user: AuthUser = Depends(require_tenant(tenant_name))
):
    """Endpoint using tenant requirement dependency."""
    return {
        "message": f"Access granted for tenant: {tenant_name}",
        "tenant": user.tenant
    }
