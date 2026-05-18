# Find Users by Tag

Use the tag route to discover users by skill, language, territory, project, or affiliation.

## Who is this for

Developers building search, discovery, recommendation, or matching experiences.

## Prerequisites

- Base URL (example: `https://capx.toolforge.org`).
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

Use quick lists to fetch IDs you can pass as `tag_id`:

```bash
curl -X GET "https://capx.toolforge.org/list/skills/"
curl -X GET "https://capx.toolforge.org/list/language/"
curl -X GET "https://capx.toolforge.org/list/territory/"
```

## Step 2: Query users for one tag

Example: users with a skill available (ID `1`).

```bash
curl -X GET "https://capx.toolforge.org/tags/skill_available/1/" \
  -H "Accept: application/json"
```

Expected result:

- `200 OK`
- Array of user profile objects.

## Step 3: Build multi-tag filtering client-side

The endpoint supports one tag at a time. For multi-tag workflows:

1. Request multiple tag combinations in parallel.
2. Intersect result sets client-side by profile ID.
3. Sort/rank according to your product logic.

## Troubleshooting

- Problem: `400 Invalid tag type`.
  - Cause: unsupported `tag_type` value.
  - Fix: use one of the documented options exactly.

- Problem: empty result array.
  - Cause: tag exists but no matching profiles.
  - Fix: verify `tag_id` or broaden search to another related tag.
