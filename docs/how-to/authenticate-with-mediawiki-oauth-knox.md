# Authenticate with MediaWiki OAuth + Knox

This guide shows the expected two-step social OAuth flow and how to call protected endpoints with the returned token.

## Who is this for

Developers integrating user-authenticated actions (bug reports, project management, and other write operations).

## Prerequisites

- Base URL (example: `https://capx-backend.toolforge.org`).
- A valid social auth provider supported by your deployment (commonly `mediawiki`).

## Step 1: Start OAuth handshake

Request temporary OAuth credentials:

```bash
curl -X POST "https://capx-backend.toolforge.org/api/login/social/knox/" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "mediawiki",
    "extra": "localhost:3001"
  }'
```

The `extra` field is optional and is used as a post-callback redirect. Think of it as the app host where login should continue after the OAuth callback.

CapX stores this value temporarily with the OAuth request token and returns it from `/api/login/social/check/` so the callback page can continue the flow in the right app.

This is a host routing mechanism for trusted apps, not a general-purpose OAuth server redirect parameter.

For security, `extra` must be either:

- A host in the backend allowlist (`OAUTH_EXTRA_ALLOWED_HOSTS`, for example `capx.toolforge.org` or `capx-test.toolforge.org`). It can be expanded over time for new trusted apps.
- `localhost` / `127.0.0.1` with or without a port (`localhost:3000`, `localhost:3001`, `127.0.0.1:3002`, etc.).

Expected result:

- `200 OK`
- Response contains temporary OAuth data, including `oauth_token` and `oauth_token_secret`.

## Step 2: Complete provider authorization

Redirect the user to the provider authorization URL using the returned temporary token.

Example URL format for MediaWiki OAuth:

```url
https://meta.wikimedia.org/w/index.php?title=Special:OAuth/authorize&oauth_token=<temporary_oauth_token>
```

After approval, collect:

- `oauth_token`
- `oauth_verifier`

## Step 3: Exchange for CapX auth token

Complete the user auth step:

```bash
curl -X POST "https://capx-backend.toolforge.org/api/login/social/knox_user/" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "mediawiki",
    "oauth_token": "<temporary_oauth_token>",
    "oauth_secret": "<temporary_oauth_secret>",
    "oauth_verifier": "<oauth_verifier_from_provider>"
  }'
```

Expected result:

- `200 OK`
- Response includes the CapX authentication token used in `Authorization` header.

## Step 4: Call a protected endpoint

Example: create a bug report.

```bash
curl -X POST "https://capx-backend.toolforge.org/bugs/" \
  -H "Authorization: Token <capx_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Example issue",
    "description": "Reproducible behavior description"
  }'
```

Expected result:

- `201 Created` on success.

## Optional: Check temporary token metadata

```bash
curl -X POST "https://capx-backend.toolforge.org/api/login/social/check/" \
  -H "Content-Type: application/json" \
  -d '{"oauth_token": "<temporary_oauth_token>"}'
```

## Troubleshooting

- Problem: `400` with missing token/verifier info.
  - Cause: incomplete payload in `knox_user` step.
  - Fix: include `provider`, `oauth_token`, `oauth_secret`, and `oauth_verifier`.

- Problem: `401 Unauthorized` on protected endpoints.
  - Cause: missing/expired token or wrong auth header format.
  - Fix: send `Authorization: Token <capx_token>` and repeat OAuth if needed.
