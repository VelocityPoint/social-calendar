# Contributing to social-calendar

This guide covers two types of contribution: authoring content (creating post documents) and contributing code (adapters, publisher, scripts, workflows).

---

## Contents

- [Content Authoring Guide](#content-authoring-guide)
  - [Post document checklist](#post-document-checklist)
  - [Writing platform copy](#writing-platform-copy)
  - [Scheduling guidelines](#scheduling-guidelines)
  - [Image assets](#image-assets)
  - [Validation before commit](#validation-before-commit)
  - [Pull request process](#pull-request-process)
- [Code Contribution Guide](#code-contribution-guide)
  - [Development setup](#development-setup)
  - [Running tests](#running-tests)
  - [Code standards](#code-standards)
  - [Branch naming](#branch-naming)
  - [Commit conventions](#commit-conventions)

---

## Content Authoring Guide

### Post document checklist

Before opening a pull request, verify each item:

- [ ] File is at the correct path: `brands/<brand>/calendar/YYYY/MM/YYYY-MM-DD-<slug>.md`
- [ ] Filename uses the format `YYYY-MM-DD-<slug>.md` (lowercase, hyphens, no spaces)
- [ ] `id` in frontmatter matches the filename without `.md`
- [ ] `publish_at` includes a timezone offset and is quoted: `'2026-04-01T09:00:00-07:00'`
- [ ] `platforms` lists at least one valid platform
- [ ] `status` is set to `scheduled`
- [ ] `brand` matches the parent brand directory name
- [ ] A `# {Platform Name} Version` section exists for every platform listed in `platforms`
- [ ] Each copy section is within the character limit for its platform
- [ ] If Instagram is a target platform, a `creative` image block is included (Instagram does not support text-only posts)
- [ ] `validate-post.py` runs clean locally

Run the validator:

```bash
python scripts/validate-post.py brands/secondring/calendar/2026/04/2026-04-01-my-post.md
```

### Writing platform copy

Each platform has distinct norms, character limits, and audiences. The document format supports independent copy per platform.

**Copy section headers must match exactly:**

| Platform | Section header |
|----------|---------------|
| LinkedIn | `# LinkedIn Version` |
| Facebook | `# Facebook Version` |
| X/Twitter | `# X Version` |
| Google Business Profile | `# Google Business Profile Version` |
| Instagram | `# Instagram Version` |

**Character limits:**

| Platform | Limit |
|----------|-------|
| LinkedIn | 3,000 |
| Facebook | 2,200 |
| X | 280 |
| Google Business Profile | 1,500 |
| Instagram | 2,200 |

The validator enforces these limits and blocks the PR if any section exceeds its limit.

**Platform considerations:**

- **LinkedIn**: Professional tone. Hashtags are used but sparingly. Line breaks add readability. Call to action at the end.
- **Facebook**: Conversational. Can be longer and more narrative. Questions drive engagement. External links are fine.
- **X**: Short, punchy, direct. Every character counts. Include the URL in the copy -- no link preview guarantee.
- **Google Business Profile**: Informational, keyword-aware. Short, scannable. Includes location-relevant context where applicable.
- **Instagram**: Visual-first. Copy supports the image. Hashtags go at the end or in a comment. Instagram requires an image -- a text-only post targeting Instagram will fail in the publisher.

**Sections for non-target platforms are ignored.** If your post targets only `linkedin` and `facebook`, you do not need X, GBP, or Instagram sections. Extra sections present in the document do not cause errors.

### Scheduling guidelines

Set `publish_at` to the intended publish time with a timezone offset. The publisher runs every 10 minutes and publishes posts within 10 minutes of the scheduled time (typically sooner if the push trigger fires immediately on merge).

Use consistent timezone offsets across posts for a given brand. The Second Ring brand defaults to Pacific Time:

- Standard time: `-08:00`
- Daylight time: `-07:00`

Or use UTC (`Z`) for unambiguous scheduling:

```yaml
publish_at: '2026-04-01T16:00:00Z'   # 9am Pacific Daylight Time
```

Allow at least 15 minutes between the PR merge and `publish_at` to account for review time and the cron schedule window.

Do not schedule multiple posts for the same platform within the same rate limit window if volume is high. The publisher defers to the next run when a rate limit is reached, which shifts the post's actual publish time.

### Image assets

Place image files in `brands/<brand>/assets/`. Reference them in the frontmatter `creative` block.

Image requirements accepted by all platforms:
- Format: JPEG
- Width: 320px minimum, 1440px maximum
- File size: under 8MB

To use different images per platform:

```yaml
creative:
  - type: image
    path: post-square-1080.jpg
    platforms:
      - instagram
  - type: image
    path: post-landscape-1200x628.jpg
    platforms:
      - linkedin
      - facebook
      - x
```

If `platforms` is omitted from a creative entry, the image is used for all platforms.

Instagram requires a public-facing URL for image uploads. The publisher derives this from `ASSETS_BASE_URL`. Images in `assets/` must be reachable at `{ASSETS_BASE_URL}/assets/{filename}` when the workflow runs.

### Validation before commit

Always validate locally before pushing:

```bash
# Install dependencies if not already installed
pip install pyyaml

# Validate one file
python scripts/validate-post.py brands/secondring/calendar/2026/04/2026-04-01-my-post.md

# Validate all posts in a month
python scripts/validate-post.py brands/secondring/calendar/2026/04/*.md
```

The `validate-pr.yml` workflow runs the same validator on every PR. If it fails, the PR cannot be merged. Fixing validation errors after push requires another commit.

### Pull request process

1. Create the post document in a branch (any branch name is fine for content).
2. Push and open a pull request against `main`.
3. The `validate-pr.yml` workflow runs automatically. Wait for it to pass.
4. Get review and approval from the content owner (for Second Ring, this is Dave).
5. Merge. The `publish.yml` workflow runs within 10 minutes (often immediately on merge).
6. After publish, the publisher commits `status: published`, `published_at`, and `post_ids` back to the document. This commit appears in the PR's branch history and on `main`.

If the post fails to publish, a GitHub issue is created labeled `publish-failure` and `agent:bob`. Check the workflow run logs for details.

---

## Code Contribution Guide

### Development setup

```bash
git clone https://github.com/VelocityPoint/social-calendar
cd social-calendar
python -m venv venv
source venv/bin/activate
pip install -r publisher/requirements.txt
pip install pyyaml  # for scripts/
```

### Running tests

There is no automated test suite in Phase 1. Test manually:

```bash
# Validate all schema files and scripts parse cleanly
python3 -m py_compile publisher/publisher.py
python3 -m py_compile publisher/models.py
python3 -m py_compile publisher/state.py
python3 -m py_compile publisher/retry.py
python3 -m py_compile publisher/adapters/base.py
python3 -m py_compile publisher/adapters/facebook.py
python3 -m py_compile publisher/adapters/instagram.py
python3 -m py_compile publisher/adapters/linkedin.py
python3 -m py_compile publisher/adapters/gbp.py
python3 -m py_compile publisher/adapters/x_twitter.py
python3 -m py_compile scripts/validate-post.py
python3 -m py_compile scripts/validate-brand.py

# Validate sample content
python scripts/validate-post.py brands/secondring/calendar/2026/04/2026-04-01-never-miss-a-call.md
python scripts/validate-brand.py brands/secondring/brand.yaml
python scripts/validate-brand.py brands/velocitypoint/brand.yaml

# Dry run publisher (no API calls)
GITHUB_TOKEN=dummy GITHUB_REPOSITORY=VelocityPoint/social-calendar \
  python -m publisher.publisher --brand secondring --dry-run
```

### Code standards

**Language:** Python 3.12. Type hints on all public functions and methods.

**Models:** Use Pydantic v2. Private fields use `PrivateAttr(default=None)`. Class-level constants use `ClassVar`.

**Logging:** Use the module-level logger (`logger = logging.getLogger(__name__)`). Log structured context in brackets: `[PUBLISHED] {post_id} on {platform}`. Business-meaningful messages, not developer noise.

**Error handling:**
- Raise `PublishError` for retryable API errors (4xx except 400 and 429, 5xx, network timeouts).
- Raise `RateLimitError` for HTTP 429 with the `Retry-After` value if available.
- Raise `PermanentError` for non-retryable errors (400, auth failures, missing data).
- Never catch and swallow publish errors in adapters. Let the retry wrapper handle them.

**Security:**
- Never pass tokens in query parameters or JSON request bodies. Use `Authorization: Bearer {token}` headers.
- Never hardcode credentials or brand-specific values in adapter code.
- The `validate-brand.py` script detects raw tokens committed to `brand.yaml`. The check looks for JWT prefixes (`eyJ`), Google prefixes (`ya29.`), Facebook prefixes (`EAA`), and suspiciously long base64 strings.

**Fail-closed gates:** Security-critical checks (like `is_committed_on_main()`) must return `False` on error, not `True`. A check that fails open is not a check.

**Adapters must:**
- Set `platform` as a class attribute matching the slug used in `ADAPTER_REGISTRY` and in post `platforms` lists.
- Accept `brand: Brand` and `state_dir: Path` in `__init__` and pass them to `super().__init__()`.
- Implement both `publish()` and `auth_check()`.
- Use `self._get_credential()` and `self._check_and_refresh_token()` for token retrieval.
- Use `self.check_rate_limit(post_id)` before API calls and `self.increment_rate_limit()` after success.
- Not make direct HTTP calls to X/Twitter API endpoints (X publishing uses `xurl` subprocess per AC15).

### Branch naming

Follow the VelocityPoint branch naming convention:

```
{agent-name}/{description}
```

Examples:
- `vulcan/add-threads-adapter`
- `vulcan/fix-linkedin-image-upload`
- `scribe/update-adapter-docs`

### Commit conventions

Reference the relevant acceptance criteria in commit messages where applicable:

```
fix: correct deferred status not re-entering queue (AC-OQ4)
feat: add Threads adapter (AC16, AC3)
docs: document retry strategy in README
chore: record publish status [skip ci]
```

The `[skip ci]` suffix is reserved for publisher-automated commits. Do not use it for manual commits.
