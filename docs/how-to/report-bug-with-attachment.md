# Report a Bug with Attachment

This guide shows how to submit a bug and then upload supporting files.

## Who is this for

Authenticated users and integrators building issue reporting tooling.

## Prerequisites

- Auth token in `Authorization: Token <token>`.
- Base URL (example: `https://capx-backend.toolforge.org`).
- File to upload (screenshot, log, or reproduction asset).

## Step 1: Create a bug report

```bash
curl -X POST "https://capx-backend.toolforge.org/bugs/" \
  -H "Authorization: Token <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Search filter mismatch",
    "description": "Expected one result, got none after applying territory filter"
  }'
```

Expected result:

- `201 Created`
- Response includes bug ID.

## Step 2: Upload an attachment for that bug

```bash
curl -X POST "https://capx-backend.toolforge.org/attachment/?bug=<bug_id>" \
  -H "Authorization: Token <token>" \
  -F "file=@screenshot.png"
```

Expected result:

- `201 Created`
- Attachment linked to the selected bug.

## Step 3: Verify your reports

```bash
curl -X GET "https://capx-backend.toolforge.org/bugs/" \
  -H "Authorization: Token <token>"

curl -X GET "https://capx-backend.toolforge.org/attachment/" \
  -H "Authorization: Token <token>"
```

Expected result:

- `200 OK`
- Non-staff users see only their own bug/attachment records.

## Troubleshooting

- Problem: `401 Unauthorized`.
  - Cause: no token or invalid token.
  - Fix: authenticate first and use `Authorization: Token <token>`.

- Problem: `400 Bad Request` on attachment create.
  - Cause: missing `bug` query parameter or missing file form part.
  - Fix: send `?bug=<id>` and `-F "file=@<path>"` in multipart request.
