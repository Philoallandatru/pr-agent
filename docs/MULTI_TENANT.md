# Multi-Tenant User Management System

Complete multi-tenant architecture with organization management, user roles, and resource isolation.

## Features

- **Organization Management**: Create and manage multiple organizations/tenants
- **User Management**: User accounts with email-based authentication
- **Role-Based Access Control**: Admin, member, and viewer roles
- **Invitation System**: Email-based invitations with expiration
- **Resource Isolation**: Tenant-scoped repositories and data
- **Usage Tracking**: Monitor resource consumption per organization
- **Quota Management**: Enforce plan-based limits

## Architecture

### Database Schema

```
organizations
├── id (PK)
├── name
├── slug (unique)
├── plan (free/pro/enterprise)
├── max_users
├── max_repositories
├── max_reviews_per_month
└── settings (JSON)

users
├── id (PK)
├── username (unique)
├── email (unique)
├── password_hash
├── full_name
├── is_active
└── is_superadmin

organization_members
├── organization_id (FK)
├── user_id (FK)
├── role (admin/member/viewer)
└── joined_at

invitations
├── token (unique)
├── organization_id (FK)
├── email
├── role
├── invited_by (FK)
├── expires_at
└── accepted_at

tenant_repositories
├── organization_id (FK)
└── repository_id (FK)

usage_tracking
├── organization_id (FK)
├── resource_type
├── count
└── period (YYYY-MM)
```

## API Endpoints

### Organizations

```http
POST   /api/tenants/organizations
GET    /api/tenants/organizations
GET    /api/tenants/organizations/{org_id}
PUT    /api/tenants/organizations/{org_id}
DELETE /api/tenants/organizations/{org_id}
```

### Users

```http
POST   /api/tenants/users
GET    /api/tenants/users/{user_id}
PUT    /api/tenants/users/{user_id}
DELETE /api/tenants/users/{user_id}
```

### Members

```http
POST   /api/tenants/organizations/{org_id}/members
GET    /api/tenants/organizations/{org_id}/members
DELETE /api/tenants/organizations/{org_id}/members/{user_id}
PUT    /api/tenants/organizations/{org_id}/members/{user_id}/role
```

### Invitations

```http
POST   /api/tenants/organizations/{org_id}/invitations
GET    /api/tenants/organizations/{org_id}/invitations
POST   /api/tenants/invitations/{token}/accept
DELETE /api/tenants/invitations/{token}
```

### Usage & Quotas

```http
GET    /api/tenants/organizations/{org_id}/usage
GET    /api/tenants/organizations/{org_id}/quota
```

## Usage Examples

### 1. Create Organization

```python
from pr_agent.tenants.manager import TenantManager

manager = TenantManager("pr_agent.db")

org_id = manager.create_organization(
    name="Acme Corp",
    slug="acme-corp",
    plan="pro"
)
```

### 2. Create User

```python
from passlib.hash import argon2

user_id = manager.create_user(
    username="john.doe",
    email="john@acme.com",
    password_hash=argon2.hash("secure_password"),
    full_name="John Doe"
)
```

### 3. Add Member to Organization

```python
# Add user as admin
manager.add_member(org_id, user_id, role="admin")

# Check membership
is_member = manager.is_member(org_id, user_id)
role = manager.get_member_role(org_id, user_id)
```

### 4. Invite New User

```python
# Create invitation
token = manager.create_invitation(
    org_id=org_id,
    email="jane@acme.com",
    role="member",
    invited_by=admin_user_id,
    expires_in_days=7
)

# Send token via email to jane@acme.com
# User accepts invitation
manager.accept_invitation(token, new_user_id)
```

### 5. Track Usage

```python
# Track API calls
manager.track_usage(org_id, "api_calls", count=10)

# Track storage
manager.track_usage(org_id, "storage", count=1024000)

# Get current usage
usage = manager.get_usage(org_id)
# Returns: {"api_calls": 10, "storage": 1024000}
```

### 6. Check Quotas

```python
# Check if organization can add more users
can_add_user = manager.check_quota(org_id, "users")

# Check if organization can add more repositories
can_add_repo = manager.check_quota(org_id, "repositories")

# Check if organization has review quota
can_review = manager.check_quota(org_id, "reviews")
```

### 7. Assign Repository to Organization

```python
# Assign repository
manager.assign_repository(org_id, repo_id)

# Get all repositories for organization
repo_ids = manager.get_organization_repositories(org_id)

# Unassign repository
manager.unassign_repository(org_id, repo_id)
```

## Role Permissions

### Admin
- Full organization management
- Add/remove members
- Update member roles
- Create invitations
- Manage repositories
- View usage and quotas

### Member
- View organization details
- View members
- Access assigned repositories
- Perform PR reviews

### Viewer
- View organization details
- View members
- Read-only access to repositories

## Plan Limits

### Free Plan
- Max users: 5
- Max repositories: 10
- Max reviews per month: 100

### Pro Plan
- Max users: 25
- Max repositories: 50
- Max reviews per month: 1000

### Enterprise Plan
- Max users: unlimited
- Max repositories: unlimited
- Max reviews per month: unlimited

## Configuration

Add to `configuration.toml`:

```toml
[multi_tenant]
enabled = true
default_plan = "free"
invitation_expiry_days = 7
enforce_quotas = true
```

## REST API Authentication

All tenant endpoints require authentication:

```python
from fastapi import Depends
from pr_agent.security.auth import get_current_user

@router.post("/organizations")
async def create_org(
    request: OrgCreate,
    current_user: dict = Depends(get_current_user)
):
    # Only authenticated users can create organizations
    org_id = tenant_manager.create_organization(...)
    return {"id": org_id}
```

## Frontend Integration

```typescript
// Create organization
const response = await api.post('/api/tenants/organizations', {
  name: 'Acme Corp',
  slug: 'acme-corp',
  plan: 'pro'
});

// Invite user
await api.post(`/api/tenants/organizations/${orgId}/invitations`, {
  email: 'user@example.com',
  role: 'member'
});

// Get organization members
const members = await api.get(`/api/tenants/organizations/${orgId}/members`);
```

## Security Considerations

1. **Password Hashing**: Always use Argon2 for password hashing
2. **Invitation Tokens**: 32-character random tokens with expiration
3. **Role Validation**: Enforce role-based permissions at API level
4. **Resource Isolation**: Ensure users can only access their organization's data
5. **Quota Enforcement**: Check quotas before allowing resource creation

## Testing

Run the test suite:

```bash
pytest tests/unittest/test_tenant_manager.py -v
```

All 25 tests cover:
- Organization CRUD operations
- User management
- Membership management
- Invitation workflow
- Usage tracking
- Quota checking

## Migration from Single-Tenant

If migrating from a single-tenant setup:

1. Create a default organization
2. Migrate existing users to the organization
3. Assign all repositories to the organization
4. Update API calls to include organization context

```python
# Migration script
default_org_id = manager.create_organization(
    name="Default Organization",
    slug="default",
    plan="enterprise"
)

# Migrate users
for user in existing_users:
    manager.add_member(default_org_id, user.id, role="admin")

# Migrate repositories
for repo in existing_repos:
    manager.assign_repository(default_org_id, repo.id)
```

## Troubleshooting

### Issue: Invitation expired
**Solution**: Create a new invitation with longer expiry period

### Issue: Quota exceeded
**Solution**: Upgrade organization plan or clean up unused resources

### Issue: Duplicate member
**Solution**: Check if user is already a member before adding

### Issue: Cannot delete organization
**Solution**: Remove all members and repositories first

## Future Enhancements

- [ ] SSO integration (SAML, OAuth)
- [ ] Custom role definitions
- [ ] Audit logging
- [ ] Billing integration
- [ ] Organization transfer
- [ ] Subdomain routing
- [ ] API rate limiting per organization
