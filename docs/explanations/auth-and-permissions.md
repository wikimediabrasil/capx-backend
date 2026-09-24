# Authentication and Permissions Model

This page explains how access control works in CapX. It helps integrators predict when a request will be allowed.

## Authentication methods

CapX uses:

- Knox token authentication
- Django REST Framework session authentication

This has a practical effect:

- Many read endpoints are public.
- Write actions usually need an authenticated user.
- Some write actions need staff or organization-manager roles.

## Permission baseline

The global REST framework default permission is:

- `IsAuthenticatedOrReadOnly`

This means:

- `GET`, `HEAD`, and `OPTIONS` are often public.
- `POST`, `PUT`, and `DELETE` usually need authentication.

Some viewsets use stricter rules. For example, bug and attachment endpoints need authentication for all actions.

## Role-sensitive operations

Common patterns in the codebase:

- Staff-only actions:
  - Create or delete organization records.
  - Update or delete bug reports and attachments.

- Manager-or-staff actions:
  - Create, update, or delete projects for managed organizations.
  - Manage project members and acceptances with organization rules.

## Error meanings

- `401 Unauthorized`: authentication is missing or invalid.
- `403 Forbidden`: the user is signed in, but is not allowed for this role or resource.
- `400 Bad Request`: the payload or business rule is not valid.

## Integration tips

- Treat role checks as dynamic. Users can gain or lose manager or staff status.
- Show clear guidance for `403` responses. Tell the user who should perform the action.
- Keep retry logic for `401` separate from `403`. A `401` often needs a new token.
