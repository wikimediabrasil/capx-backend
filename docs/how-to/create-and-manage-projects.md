# Create and Manage Projects

This guide covers the main project workflow: create a project, add an organization member, and process acceptance.

## Who this guide is for

Organization managers and staff who integrate project collaboration flows.

## Prerequisites

- An auth token in `Authorization: Token <token>`.
- At least one valid organization ID.
- Base URL. Example: `https://capx-backend.toolforge.org`.

## Step 1: Create a project

```bash
curl -X POST "https://capx-backend.toolforge.org/projects/" \
  -H "Authorization: Token <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Cross-community Campaign",
    "description": "Shared initiative",
    "organization": 10
  }'
```

Expected result:

- `201 Created`
- A project record is created.

## Step 2: Add another organization as a project member

```bash
curl -X POST "https://capx-backend.toolforge.org/project_members/" \
  -H "Authorization: Token <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "project": 42,
    "organization": 25
  }'
```

Expected result:

- `201 Created` when the caller is allowed.

## Step 3: Accept the project membership invitation

```bash
curl -X POST "https://capx-backend.toolforge.org/project_member_acceptance/" \
  -H "Authorization: Token <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "project_member": 77,
    "accepted": true
  }'
```

Expected result:

- `201 Created` when the invited organization manager accepts.

## Step 4: Update or remove a project

- Update endpoint: `PUT /projects/{id}/`
- Delete endpoint: `DELETE /projects/{id}/`

Authorization checks depend on staff role and organization manager membership.

## Troubleshooting

- Problem: `403 Forbidden` during create, update, or delete.
  - Cause: the caller is not staff and is not the manager of the relevant organization.
  - Fix: sign in as an authorized manager or staff user.

- Problem: `400 Bad Request` when you create an acceptance.
  - Cause: an acceptance record already exists for the same project member.
  - Fix: fetch the existing acceptance and avoid a duplicate create.
