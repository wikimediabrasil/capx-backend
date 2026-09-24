# Authenticate with MediaWiki OAuth + Knox

This guide shows a two-step login flow. Use it to call protected endpoints with the token that you receive.

## Who this guide is for

Developers who need signed-in actions, such as bug reports, project work, and other write actions.

## Prerequisites

- Base URL. Example: `https://capx-backend.toolforge.org`.
- A supported social login provider. In many cases, this is `mediawiki`.

## Step 1: Start the OAuth handshake

Request temporary OAuth credentials:

```bash
curl -X POST "https://capx-backend.toolforge.org/api/login/social/knox/" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "mediawiki",
    "extra": "localhost:3001"
  }'
```

The `extra` field is optional. It tells the app where login should continue after the OAuth callback.

CapX stores this value for the short term with the OAuth request token. It also returns it from `/api/login/social/check/` so the callback page can continue in the right app.

This is a host-routing option for trusted apps. It is not a general OAuth redirect parameter.

For security, `extra` must be one of these:

- A host in the backend allowlist. Example: `capx.toolforge.org` or `capx-test.toolforge.org`.
- `localhost` or `127.0.0.1`, with or without a port. Example: `localhost:3000` or `127.0.0.1:3002`.

Expected result:

- `200 OK`
- The response includes temporary OAuth data, such as `oauth_token` and `oauth_token_secret`.

## Step 2: Complete provider authorization

Send the user to the provider authorization URL with the temporary token.

Example URL format for MediaWiki OAuth:

```url
https://meta.wikimedia.org/w/index.php?title=Special:OAuth/authorize&oauth_token=<temporary_oauth_token>
```

After approval, collect:

- `oauth_token`
- `oauth_verifier`

## Step 3: Exchange the token for a CapX auth token

Complete the sign-in step:

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
- The response includes the CapX auth token for the `Authorization` header.

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

- Problem: `400` with missing token or verifier data.
  - Cause: the `knox_user` payload is incomplete.
  - Fix: include `provider`, `oauth_token`, `oauth_secret`, and `oauth_verifier`.

- Problem: `401 Unauthorized` on protected endpoints.
  - Cause: the token is missing, expired, or in the wrong header format.
  - Fix: send `Authorization: Token <capx_token>` and repeat the OAuth flow if needed.
