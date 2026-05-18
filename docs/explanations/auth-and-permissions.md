# Authentication and Permissions Model

This page explains how access control works in CapX so integrators can anticipate authorization outcomes.

## Authentication Methods

CapX is configured with:

- Knox token authentication
- Django REST Framework session authentication

Practical impact:

- Public read access is available on many endpoints.
- Write operations usually require authenticated users.
- Some write operations require staff or organization-manager roles.

## Permission Baseline

Global REST framework default permission is:

- `IsAuthenticatedOrReadOnly`

This means:

- `GET/HEAD/OPTIONS` are often public.
- `POST/PUT/DELETE` usually need authentication.

Some viewsets override this with stricter rules (for example bug and attachment endpoints require authentication for all operations).

## Role-Sensitive Operations

Common patterns in the codebase:

- Staff-only actions:
  - Creating/deleting organization records.
  - Updating/deleting bug reports and attachments.

- Manager-or-staff actions:
  - Creating/updating/deleting projects linked to managed organizations.
  - Managing project members and acceptances with organization constraints.

## Error Semantics

- `401 Unauthorized`: authentication missing/invalid.
- `403 Forbidden`: authenticated but not allowed for the role/resource.
- `400 Bad Request`: payload or business-rule validation failure.

## Integration Tips

- Treat role checks as dynamic: users may gain/lose manager/staff status.
- Surface clear UX guidance for `403` responses (who should perform the action).
- Keep retry logic for `401` (token refresh/re-auth) separate from `403` (permission issue).
