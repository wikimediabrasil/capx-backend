# First API Call

This tutorial helps you make a first successful request and understand how to move between workflow guides and OpenAPI reference.

## Prerequisites

- A running CapX backend instance.
- Base URL (for production: `https://capx.toolforge.org`).

## Step 1: Open the API reference

Open Swagger UI in your browser:

- `https://capx.toolforge.org/`

The raw schema is available at:

- `https://capx.toolforge.org/schema/`

## Step 2: Make a public GET request

Start with a public endpoint that does not require authentication:

```bash
curl -X GET "https://capx.toolforge.org/list/skills/" \
  -H "Accept: application/json"
```

Expected result:

- `200 OK`
- A JSON object mapping skill IDs to labels.

## Step 3: Try a filtered discovery endpoint

Use tag search to list profiles by a specific tag type and tag ID:

```bash
curl -X GET "https://capx.toolforge.org/tags/skill_available/1/" \
  -H "Accept: application/json"
```

Expected result:

- `200 OK`
- A JSON array of matching profiles.

## Step 4: Continue with authenticated workflows

For write operations (create, update, delete), continue with:

- [Authenticate with MediaWiki OAuth + Knox](../how-to/authenticate-with-mediawiki-oauth-knox.md)

## Troubleshooting

- Problem: `404 Not Found`
  - Cause: wrong route or missing trailing slash.
  - Fix: confirm the exact path in Swagger UI and keep trailing slashes.

- Problem: `401 Unauthorized` or `403 Forbidden`
  - Cause: endpoint requires authentication/permissions.
  - Fix: follow the auth guide and include `Authorization: Token <token>`.
