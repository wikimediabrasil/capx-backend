# First API Call

This guide helps you make one successful request. It also shows how to move from this guide to Swagger and OpenAPI.

## Prerequisites

- A running CapX backend.
- Base URL. Example: `https://capx-backend.toolforge.org`.

## Step 1: Open the API reference

Open Swagger UI in a browser:

- `https://capx-backend.toolforge.org/`

The raw schema is at:

- `https://capx-backend.toolforge.org/schema/`

## Step 2: Make a public GET request

Use a public endpoint that does not need authentication:

```bash
curl -X GET "https://capx-backend.toolforge.org/list/skills/" \
  -H "Accept: application/json"
```

Expected result:

- `200 OK`
- A JSON object with skill IDs and labels.

## Step 3: Try a filtered discovery endpoint

Use tag search to list profiles by a tag type and tag ID:

```bash
curl -X GET "https://capx-backend.toolforge.org/tags/wikimedia_project/1/" \
  -H "Accept: application/json"
```

Expected result:

- `200 OK`
- A JSON array of matching profiles.

## Step 4: Continue with authenticated workflows

For write actions, continue with:

- [Authenticate with MediaWiki OAuth + Knox](../how-to/authenticate-with-mediawiki-oauth-knox.md)

## Troubleshooting

- Problem: `404 Not Found`
  - Cause: wrong route or missing trailing slash.
  - Fix: check the path in Swagger UI and keep the trailing slash.

- Problem: `401 Unauthorized` or `403 Forbidden`
  - Cause: the endpoint needs authentication or permission.
  - Fix: follow the auth guide and send `Authorization: Token <token>`.
