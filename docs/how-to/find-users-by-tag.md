# Find Users by Tag

Use the tag route to find users by skill, language, territory, project, or affiliation.

## Who this guide is for

Developers who build search, discovery, recommendation, or matching features.

## Prerequisites

- Base URL. Example: `https://capx-backend.toolforge.org`.
- A valid tag type and tag ID.

Supported tag types:

- `skill_known`
- `skill_available`
- `skill_wanted`
- `language`
- `territory`
- `wikimedia_project`
- `affiliation`

## Step 1: Get candidate IDs

Use the quick list endpoints to get IDs that you can pass as `tag_id`:

```bash
curl -X GET "https://capx-backend.toolforge.org/list/skills/"
curl -X GET "https://capx-backend.toolforge.org/list/language/"
curl -X GET "https://capx-backend.toolforge.org/list/territory/"
```

## Step 2: Query users for one tag

Example: users with a skill available (ID `1`).

```bash
curl -X GET "https://capx-backend.toolforge.org/tags/skill_available/1/" \
  -H "Accept: application/json"
```

Expected result:

- `200 OK`
- An array of user profile objects.

## Step 3: Build multi-tag filtering on the client

The endpoint uses one tag at a time. For multi-tag work:

1. Request several tag combinations.
2. Combine the results by profile ID.
3. Sort or rank the results by your product rules.

## Troubleshooting

- Problem: `400 Invalid tag type`.
  - Cause: the tag type is not supported.
  - Fix: use one of the documented values exactly.

- Problem: empty result array.
  - Cause: the tag exists, but no profile matches it.
  - Fix: check the `tag_id` or use a related tag.
