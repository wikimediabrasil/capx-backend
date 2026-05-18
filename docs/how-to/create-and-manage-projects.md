# Create and Manage Projects

This guide covers the core project workflow: create project, add organization members, and process acceptance.

## Who is this for

Organization managers and staff integrating project collaboration flows.

## Prerequisites

- Auth token in `Authorization: Token <token>`.
- At least one valid organization ID.
- Base URL (example: `https://capx.toolforge.org`).

## Step 1: Create a project

```bash
curl -X POST "https://capx.toolforge.org/projects/" \
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

## Step 2: Add another organization as project member

```bash
curl -X POST "https://capx.toolforge.org/project_members/" \
  -H "Authorization: Token <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "project": 42,
    "organization": 25
  }'
```

Expected result:

- `201 Created` when caller is allowed.

## Step 3: Accept project membership invitation

```bash
curl -X POST "https://capx.toolforge.org/project_member_acceptance/" \
  -H "Authorization: Token <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "project_member": 77,
    "accepted": true
  }'
```

Expected result:

- `201 Created` when invited organization manager accepts.

## Step 4: Update or remove project

- Update endpoint: `PUT /projects/{id}/`
- Delete endpoint: `DELETE /projects/{id}/`

Authorization checks apply based on staff role and organization manager membership.

## Troubleshooting

- Problem: `403 Forbidden` during create/update/delete.
  - Cause: caller is not staff and not manager of relevant organization(s).
  - Fix: authenticate as authorized manager or staff user.

- Problem: `400 Bad Request` creating acceptance.
  - Cause: acceptance record already exists for the same project member.
  - Fix: fetch existing acceptance and avoid duplicate create.
