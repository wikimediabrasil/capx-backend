# Versioning and Change Policy

Use this policy to keep API clients stable while the platform changes.

## Source of truth

- Endpoint contracts come from OpenAPI at `/schema/`.
- Human-readable docs in `docs/` explain workflows and integration behavior.

## Suggested compatibility rules

1. Non-breaking changes can ship in normal releases.

- Add optional request fields.
- Add response fields without changing their meaning.
- Add new endpoints.

2. Breaking changes need migration guidance.

- Rename or remove fields.
- Change field types or meaning.
- Remove endpoints.

3. Deprecation should be clear.

- Mark endpoints as deprecated in OpenAPI where possible.
- Keep deprecated behavior for a defined transition period.
- Provide a replacement endpoint and migration steps.

## Pull request documentation gate

For any API behavior change, include all relevant items in one pull request:

1. Code changes.
2. OpenAPI updates.
3. Guide updates in `docs/how-to` or `docs/tutorials`.
4. A changelog note, if your release process uses one.

## Recommended release checklist

1. Regenerate the schema file if it is tracked in the repository.
2. Check Swagger examples.
3. Validate the key guides with real requests.
4. Announce breaking or deprecated changes with upgrade notes.
