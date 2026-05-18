# Versioning and Change Policy

Use this policy to keep API consumers stable while the platform evolves.

## Source of Truth

- Endpoint contracts are defined by OpenAPI at `/schema/`.
- Human-readable docs in `docs/` explain workflows and integration behavior.

## Suggested Compatibility Rules

1. Non-breaking changes can ship in normal releases.

- Adding optional request fields.
- Adding response fields without changing existing meanings.
- Adding new endpoints.

2. Breaking changes require migration guidance.

- Renaming/removing fields.
- Changing field types/semantics.
- Removing endpoints.

3. Deprecation should be explicit.

- Mark endpoints as deprecated in OpenAPI where possible.
- Keep deprecated behavior available for a defined transition period.
- Provide replacement endpoint and migration steps.

## Pull Request Documentation Gate

For any API behavior change, include all relevant artifacts in one pull request:

1. Code changes.
2. OpenAPI updates.
3. Guide updates in `docs/how-to` or `docs/tutorials`.
4. Changelog note (if your release process includes one).

## Recommended Release Checklist

1. Regenerate schema file if tracked in-repo.
2. Spot-check Swagger examples.
3. Validate key guides with real requests.
4. Announce breaking/deprecated changes with upgrade notes.
