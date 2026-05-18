# CapX API Documentation

This folder contains task-oriented API documentation that complements the OpenAPI reference.

## Documentation Map

Use this structure to keep docs useful for both new and advanced integrators:

- Tutorials: step-by-step learning paths.
- How-to guides: practical workflows and recipes.
- Explanations: concepts and behavior details.
- Reference: OpenAPI and endpoint-level source of truth.

## Start Here

1. Tutorial: [First API Call](tutorials/first-api-call.md)
2. How-to: [Authenticate with MediaWiki OAuth + Knox](how-to/authenticate-with-mediawiki-oauth-knox.md)
3. How-to: [Find Users by Tag](how-to/find-users-by-tag.md)
4. How-to: [Create and Manage Projects](how-to/create-and-manage-projects.md)
5. How-to: [Report a Bug with Attachment](how-to/report-bug-with-attachment.md)
6. Explanation: [Authentication and Permissions Model](explanations/auth-and-permissions.md)
7. Explanation: [Versioning and Change Policy](explanations/versioning-and-change-policy.md)

## OpenAPI Reference

- Swagger UI (interactive): `/`
- OpenAPI schema endpoint: `/schema/`
- Reference notes: [Reference README](reference/README.md)

## Authoring Rules

- Keep guides task-oriented, not endpoint-oriented.
- Include prerequisites, request examples, expected outcomes, and troubleshooting.
- Link each workflow step to the relevant endpoint in Swagger/OpenAPI.
- Prefer real, minimal payloads over large synthetic examples.

## Contributing a New Guide

Use the template in [How-to Template](templates/how-to-template.md).
