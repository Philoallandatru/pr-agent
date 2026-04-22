"""
Tenant Management API Routes

Provides REST API endpoints for multi-tenant organization and user management.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel

from pr_agent.security import get_current_user, User
from pr_agent.tenants.manager import TenantManager
from pr_agent.log import get_logger

# Create router
router = APIRouter(prefix="/api/tenants", tags=["tenants"])

# This will be set by the main app
tenant_manager: Optional[TenantManager] = None


def set_tenant_manager(manager: TenantManager):
    """Set the tenant manager instance."""
    global tenant_manager
    tenant_manager = manager


# Pydantic models
class OrganizationCreate(BaseModel):
    name: str
    slug: str
    plan: str = "free"


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    plan: Optional[str] = None


class MemberAdd(BaseModel):
    user_id: int
    role: str = "member"


class InvitationCreate(BaseModel):
    email: str
    role: str = "member"
    expires_in_days: int = 7


# Organization endpoints
@router.post("/organizations", status_code=201)
async def create_organization(
    org: OrganizationCreate,
    current_user: User = Depends(get_current_user),
):
    """Create a new organization."""
    try:
        org_id = tenant_manager.create_organization(
            name=org.name,
            slug=org.slug,
            plan=org.plan
        )

        # Add creator as admin
        tenant_manager.add_member(org_id, current_user.user_id, "admin")

        organization = tenant_manager.get_organization(org_id)
        get_logger().info(f"Organization created: {org.slug} by user {current_user.username}")

        return organization
    except Exception as e:
        get_logger().error(f"Failed to create organization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/organizations")
async def list_organizations(current_user: User = Depends(get_current_user)):
    """List all organizations the current user belongs to."""
    try:
        organizations = tenant_manager.get_user_organizations(current_user.user_id)
        return {"organizations": organizations}
    except Exception as e:
        get_logger().error(f"Failed to list organizations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/organizations/{org_id}")
async def get_organization(
    org_id: int,
    current_user: User = Depends(get_current_user),
):
    """Get organization details."""
    try:
        if not tenant_manager.is_member(org_id, current_user.user_id):
            raise HTTPException(status_code=403, detail="Not a member of this organization")

        organization = tenant_manager.get_organization(org_id)
        if not organization:
            raise HTTPException(status_code=404, detail="Organization not found")

        return organization
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to get organization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/organizations/{org_id}")
async def update_organization(
    org_id: int,
    org_update: OrganizationUpdate,
    current_user: User = Depends(get_current_user),
):
    """Update organization (admin only)."""
    try:
        role = tenant_manager.get_member_role(org_id, current_user.user_id)
        if role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")

        tenant_manager.update_organization(
            org_id=org_id,
            name=org_update.name,
            plan=org_update.plan
        )

        organization = tenant_manager.get_organization(org_id)
        get_logger().info(f"Organization {org_id} updated by user {current_user.username}")

        return organization
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to update organization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/organizations/{org_id}")
async def delete_organization(
    org_id: int,
    current_user: User = Depends(get_current_user),
):
    """Delete organization (admin only)."""
    try:
        role = tenant_manager.get_member_role(org_id, current_user.user_id)
        if role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")

        tenant_manager.delete_organization(org_id)
        get_logger().info(f"Organization {org_id} deleted by user {current_user.username}")

        return {"message": "Organization deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to delete organization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Member management endpoints
@router.get("/organizations/{org_id}/members")
async def list_members(
    org_id: int,
    current_user: User = Depends(get_current_user),
):
    """List organization members."""
    try:
        if not tenant_manager.is_member(org_id, current_user.user_id):
            raise HTTPException(status_code=403, detail="Not a member of this organization")

        members = tenant_manager.get_organization_members(org_id)
        return {"members": members}
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to list members: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/organizations/{org_id}/members")
async def add_member(
    org_id: int,
    member: MemberAdd,
    current_user: User = Depends(get_current_user),
):
    """Add member to organization (admin only)."""
    try:
        role = tenant_manager.get_member_role(org_id, current_user.user_id)
        if role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")

        success = tenant_manager.add_member(org_id, member.user_id, member.role)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to add member")

        get_logger().info(f"User {member.user_id} added to org {org_id} by {current_user.username}")

        return {"message": "Member added successfully"}
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to add member: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/organizations/{org_id}/members/{user_id}")
async def remove_member(
    org_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
):
    """Remove member from organization (admin only)."""
    try:
        role = tenant_manager.get_member_role(org_id, current_user.user_id)
        if role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")

        # Cannot remove yourself
        if user_id == current_user.user_id:
            raise HTTPException(status_code=400, detail="Cannot remove yourself")

        tenant_manager.remove_member(org_id, user_id)
        get_logger().info(f"User {user_id} removed from org {org_id} by {current_user.username}")

        return {"message": "Member removed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to remove member: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/organizations/{org_id}/members/{user_id}/role")
async def update_member_role(
    org_id: int,
    user_id: int,
    role: str = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
):
    """Update member role (admin only)."""
    try:
        current_role = tenant_manager.get_member_role(org_id, current_user.user_id)
        if current_role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")

        tenant_manager.update_member_role(org_id, user_id, role)
        get_logger().info(f"User {user_id} role updated to {role} in org {org_id}")

        return {"message": "Member role updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to update member role: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Invitation endpoints
@router.post("/organizations/{org_id}/invitations")
async def create_invitation(
    org_id: int,
    invitation: InvitationCreate,
    current_user: User = Depends(get_current_user),
):
    """Create invitation (admin only)."""
    try:
        role = tenant_manager.get_member_role(org_id, current_user.user_id)
        if role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")

        token = tenant_manager.create_invitation(
            org_id=org_id,
            email=invitation.email,
            role=invitation.role,
            invited_by=current_user.user_id,
            expires_in_days=invitation.expires_in_days
        )

        get_logger().info(f"Invitation created for {invitation.email} to org {org_id}")

        return {
            "token": token,
            "email": invitation.email,
            "role": invitation.role,
            "expires_in_days": invitation.expires_in_days
        }
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to create invitation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/invitations/{token}/accept")
async def accept_invitation(
    token: str,
    current_user: User = Depends(get_current_user),
):
    """Accept invitation."""
    try:
        success = tenant_manager.accept_invitation(token, current_user.user_id)
        if not success:
            raise HTTPException(status_code=400, detail="Invalid or expired invitation")

        get_logger().info(f"User {current_user.username} accepted invitation {token}")

        return {"message": "Invitation accepted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to accept invitation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Usage tracking endpoints
@router.get("/organizations/{org_id}/usage")
async def get_usage(
    org_id: int,
    period: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """Get organization usage statistics."""
    try:
        if not tenant_manager.is_member(org_id, current_user.user_id):
            raise HTTPException(status_code=403, detail="Not a member of this organization")

        usage = tenant_manager.get_usage(org_id, period)
        return {"usage": usage, "period": period}
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to get usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/organizations/{org_id}/quota")
async def check_quota(
    org_id: int,
    resource_type: str,
    current_user: User = Depends(get_current_user),
):
    """Check if organization has quota available."""
    try:
        if not tenant_manager.is_member(org_id, current_user.user_id):
            raise HTTPException(status_code=403, detail="Not a member of this organization")

        available = tenant_manager.check_quota(org_id, resource_type)
        return {"resource_type": resource_type, "available": available}
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to check quota: {e}")
        raise HTTPException(status_code=500, detail=str(e))
