# Report a Bug with Attachment

This guide shows how to send a bug report and then upload a file with it.

## Who this guide is for

Signed-in users and integrators who build issue reporting tools.

## Prerequisites

- An auth token in `Authorization: Token <token>`.
- Base URL. Example: `https://capx-backend.toolforge.org`.
- A file to upload, such as a screenshot, log, or reproduction asset.

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
- The response includes the bug ID.

## Step 2: Upload an attachment for that bug

```bash
curl -X POST "https://capx-backend.toolforge.org/attachment/?bug=<bug_id>" \
  -H "Authorization: Token <token>" \
  -F "file=@screenshot.png"
```

Expected result:

- `201 Created`
- The attachment is linked to the selected bug.

## Step 3: Check your reports

```bash
curl -X GET "https://capx-backend.toolforge.org/bugs/" \
  -H "Authorization: Token <token>"

curl -X GET "https://capx-backend.toolforge.org/attachment/" \
  -H "Authorization: Token <token>"
```

Expected result:

- `200 OK`
- Non-staff users see only their own bug and attachment records.

## Troubleshooting

- Problem: `401 Unauthorized`.
  - Cause: the token is missing or invalid.
  - Fix: sign in first and use `Authorization: Token <token>`.

- Problem: `400 Bad Request` when you create an attachment.
  - Cause: the `bug` query parameter or file part is missing.
  - Fix: send `?bug=<id>` and `-F "file=@<path>"` in the multipart request.
