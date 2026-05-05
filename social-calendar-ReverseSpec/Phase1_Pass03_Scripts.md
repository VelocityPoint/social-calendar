# Phase 1 — Pass 03 — Operator Scripts

**Snapshot:** `67d061c`
**Scope:** `scripts/ghl_social.py` (363 LOC), `scripts/validate-brand.py` (170 LOC), `scripts/validate-post.py` (325 LOC). Total **858 LOC**.

**Resolves Pass 0 finding #2** (`AC_VERIFICATION_SUMMARY.md` cites 4 separate `ghl_social_*.py` scripts that don't exist in repo). Confirmed: those 4 CLIs have been consolidated into one `ghl_social.py` with 4 subcommands. See `ghl_social.py` § Subcommand Inventory below.

---

### `scripts/ghl_social.py`

**Module docstring (lines 1-46):** "GHL Social Planner CLI" — operator-only CLI wrapping `publisher.adapters.ghl.GHLAdapter`.

**1. CLI surface (argparse, `build_parser`, lines 296-343)**

Global args (apply to every subcommand):
- `--location-id ID` (default: `$GHL_LOCATION_ID`) — line 305
- `--api-key KEY` (default: `$GHL_API_KEY`) — line 307
- `--verbose, -v` — line 309

Subcommands (`sub.required = True`, line 312) — exactly **4**:

| Subcommand | Required args | Optional args | Handler | Lines |
|---|---|---|---|---|
| `accounts` | (none) | `--json` | `cmd_accounts` | 315-316, 126-150 |
| `posts` | (none) | `--status {scheduled,published,failed,draft}`, `--from DATE`, `--to DATE`, `--limit N` (default 50), `--json` | `cmd_posts` | 319-327, 157-198 |
| `create` | `--account-id ID`, `--content TEXT` | `--schedule-at ISO`, `--image-url URL`, `--dry-run` | `cmd_create` | 330-336, 205-243 |
| `delete` | `--post-id ID` | `--dry-run` | `cmd_delete` | 339-341, 250-289 |

**2. Operator workflows supported (Subcommand Inventory — resolves consolidation finding)**

The 4 subcommands directly correspond to the 4 missing scripts cited by `AC_VERIFICATION_SUMMARY.md`:

| Stale doc reference (`AC_VERIFICATION_SUMMARY.md`) | Current location |
|---|---|
| `scripts/ghl_social_list_accounts.py` | `ghl_social.py accounts` (cmd_accounts, line 126) |
| `scripts/ghl_social_list_posts.py` | `ghl_social.py posts` (cmd_posts, line 157) |
| `scripts/ghl_social_create_post.py` | `ghl_social.py create` (cmd_create, line 205) |
| `scripts/ghl_social_delete_post.py` | `ghl_social.py delete` (cmd_delete, line 250) |

`scripts/publish_posts.py` (also cited by AC summary) is NOT a subcommand of `ghl_social.py`; per Pass 0 component map, the publish path is `publisher.publisher` invoked via `publish.yml`, not `scripts/`. UNKNOWN whether `publish_posts.py` ever existed or was always a doc error. Note: `validate-post.py:251` still references the old name `ghl_social_list_accounts.py` in an error message — stale string after consolidation.

The `accounts` subcommand specifically supports the **discover-accounts workflow** referenced in `brand.yaml` comments (per Pass 0). Use case: operator runs `ghl_social.py accounts --json | jq '.[].id'` (line 29) to find account IDs for the `ghl.accounts` block in `brand.yaml`.

**3. GHL API calls — endpoints + payloads**

Adapter dispatch is delegated to `GHLAdapter` (`publisher/adapters/ghl.py`) — out of scope for this pass except where the CLI shells direct calls:

- `cmd_accounts` (line 131): `adapter.get_accounts()` — endpoint UNKNOWN at this pass (Pass 02 resolves)
- `cmd_posts` (line 172): `adapter.list_posts(filters)` with `filters` keys: `status`, `startDate`, `endDate`, `limit` — endpoint UNKNOWN (Pass 02)
- `cmd_create` (line 236): direct `adapter._request("POST", f"/social-media-posting/{location_id}/posts", payload)` — payload shape (lines 210-217):
  ```
  {"accountIds": [account_id],
   "content": <text>,
   "scheduledAt": <ISO>,
   "type": "image" if image_url else "text",
   "mediaUrls": [image_url]   # only if --image-url}
  ```
- `cmd_delete` (line 273): `adapter.delete(post_id)` — dry-run shows `DELETE /social-media-posting/{location_id}/posts/{post_id}` (line 257)

**4. Output format**

Two modes per subcommand that supports it:
- Default: aligned text table via `table()` helper (lines 95-114). Columns:
  - `accounts`: `ACCOUNT_ID`, `PLATFORM`, `NAME`, `STATUS` (line 149)
  - `posts`: `POST_ID`, `STATUS`, `SCHEDULED_AT`, `PLATFORMS`, `CONTENT_PREVIEW` (lines 191-197); content preview truncated to 45 chars by `truncate()` (line 117)
- `--json`: `json.dumps(..., indent=2)` to stdout (lines 137, 178) — pipeable via `jq`

`create` (dry-run) prints multi-line summary with `[DRY RUN]` prefix (lines 220-224); on success prints "Post created. GHL Post ID: …" + JSON dump (lines 238-239).

`delete` (dry-run) prints `[DRY RUN]` summary (lines 255-258); live mode requires user to type the post ID for confirmation (line 262).

**Safety / interaction patterns:**
- `create --dry-run` is documented in usage as "always dry-run first" (line 36). Live mode prompts "Press Enter to continue or Ctrl+C to cancel" (line 227).
- `delete` live mode requires the operator to type the exact post ID; mismatch → exit 1 (line 265). 404/401/403 surfaced by status (lines 280-283).
- All commands return int exit codes (0=ok, 1=err); credential check via `check_credentials()` returns 1 on missing `GHL_API_KEY` or `GHL_LOCATION_ID` (lines 85-92).

**5. AC refs**

No AC references appear in the file (no `AC` substring matches in the source). The script is an operator tool; AC compliance lives in `validate-*.py` and `publisher/`. Pass 0 cited it as resolving "discover-accounts (per brand.yaml comment)" — confirmed by docstring example (line 29).

---

### `scripts/validate-brand.py`

**Module docstring (lines 1-13):** "Brand config validator (AC8)". Single AC reference.

**1. CLI surface**

Plain `sys.argv` parsing (no argparse). Lines 146-167:
```
Usage: validate-brand.py <brand.yaml> [brand2.yaml ...]
```
- Positional: 1+ YAML file paths
- No flags

**2. What's validated**

Schema check on `brands/<brand>/brand.yaml`:

| Validator | Lines | Rule |
|---|---|---|
| Required fields | 21, 117-119 | `brand_name`, `credentials`, `cadence`, `pillars` must all be present and non-null |
| `brand_name` type | 122-123 | must be string |
| `credentials` (AC8) | 46-62, 125-127 | must be dict; keys must be in `VALID_PLATFORMS = {"facebook", "linkedin", "gbp", "x", "instagram"}` (line 22); each value run through `check_raw_token()` (line 36) |
| `cadence` | 65-97, 130-131 | must be non-empty dict; each platform entry must have `posts_per_week` (positive int) and `preferred_times` (non-empty list of `HH:MM` strings, regex line 33) |
| `pillars` | 134-136 | must be non-empty list |
| `avatar_id` | 139-141 | optional; if present, must be string or null (Phase 1 OK per comment line 138) |

**KV-secret-name format vs raw token detection (AC8 — security):**

Lines 25-31 — patterns flagged as raw tokens (NOT KV secret names):
- `^eyJ` → JWT
- `^ya29\.` → Google OAuth
- `^EAA` → Facebook/Meta access token
- `^AAAAAA` → Twitter/X bearer token
- `[A-Za-z0-9+/]{100,}={0,2}$` → long base64 (likely raw token)

Error message: "Store the Key Vault secret name, not the token itself." (line 60).

The validator does NOT positively assert KV secret-name *format* (e.g., `kv-<brand>-<platform>-token` per Pass 0 reference). It only rejects values that look like raw tokens. UNKNOWN whether the positive-format check lives elsewhere or is intentionally absent.

`account_id format` is NOT validated by this script — `account_id` lives under `ghl.accounts` in `brand.yaml`, but this validator only enforces the 4 `REQUIRED_FIELDS` listed above; the `ghl` block is not checked here (or anywhere else surfaced in this pass).

**3. CI gate role**

Yes — `.github/workflows/validate-pr.yml` lines 51-65:
```
- name: Validate changed brand configs
  run: |
    CHANGED_BRANDS=$(git diff --name-only origin/${{ github.base_ref }}...HEAD \
      | grep 'brands/.*/brand\.yaml' || true)
    ...
    echo "$CHANGED_BRANDS" | xargs python scripts/validate-brand.py
```
Triggered on PR to `main` when `brands/**/brand.yaml` changes (workflow `paths`, line 13).

**4. Exit codes**

Per docstring (lines 8-10) and `main()` (lines 163-166):
- `0` — all files valid
- `1` — one or more validation errors (errors printed to stderr, prefixed with `<file>: `)

**5. AC refs**

Only **AC8** in module docstring (line 3) and inline comment (line 125: `# Validate credentials (AC8 — security: detect raw tokens)`). No other AC tags in this file.

---

### `scripts/validate-post.py`

**Module docstring (lines 1-21):** "Post document schema validator (AC1, AC5, AC8, AC11, AC-OQ2, AC-OQ3)". Multi-AC.

**1. CLI surface**

Manual `sys.argv` parsing (no argparse). Lines 278-321:
- Positional: 1+ markdown file paths (supports glob expansion via shell)
- `--dry-run` / `-n` — accepted for CLI consistency, no-op (lines 286-293; comment line 16: "validate-post.py never writes anything — this flag is included for consistency with the publisher CLI and AC8 acceptance criteria")

**2. What's validated, by AC**

Per `post.schema.yaml` (Pass 04 — schema not read this pass; rules below are what the validator enforces):

| Rule | AC ref | Lines | Detail |
|---|---|---|---|
| File path matches `brands/<brand>/calendar/YYYY/MM/YYYY-MM-DD-<slug>.md` | AC-OQ2 | 64-66, 126-131 | regex `FILE_PATH_PATTERN` |
| Filename matches `YYYY-MM-DD-<slug>.md` | AC-OQ2 | 63, 133-137 | regex `FILENAME_PATTERN` |
| YAML frontmatter present (file starts with `---`) | AC1 | 156-158 | |
| Required fields: `id`, `publish_at`, `platforms`, `status`, `brand`, `author` | AC1, AC8 | 33, 161-170 | "missing required field" |
| `id` matches `YYYY-MM-DD-<slug>` | AC1 | 62, 173-177 | regex `POST_ID_PATTERN` |
| `publish_at` ISO 8601 with timezone offset (`+HH:MM` or `Z`) | AC1, **AC5** | 59-61, 180-187 | regex `PUBLISH_AT_PATTERN` — explicit "must include timezone offset" message; example `2026-04-01T09:00:00-07:00` |
| `platforms` non-empty list of `{facebook,linkedin,gbp,x,instagram}` | AC1 | 34, 189-203 | enum `VALID_PLATFORMS` |
| `status` in `{draft,ready,scheduled,published,failed,deferred,video-pending}` | AC1, AC8 | 35-37, 205-213 | enum `VALID_STATUSES`; lifecycle hint in error: "draft → ready → scheduled → published \| failed" |
| `author` in `{dave, velocitypoint}` (when `ghl_mode` true) | AC8 | 50, 220-227 | enum `VALID_AUTHORS`; suggests `ghl_mode: false` to bypass |
| `author` resolves in `brands/<brand>/brand.yaml → ghl.accounts` | AC8 | 99-112, 228-241 | hard-fail if `ghl.accounts` populated AND author missing; **silent pass** if `ghl.accounts` is empty/absent (comment line 232: "Step 4 (brand config) adds the ghl block; Step 3 should not block on it") |
| Each listed platform has `account_id` for that author | AC8 | 244-251 | hard-fail; suggests running `ghl_social_list_accounts.py` (STALE — should be `ghl_social.py accounts`, see cross-cutting note) |
| Per-platform copy section header present (`# LinkedIn Version`, etc.) | **AC11**, AC-OQ3 | 52-58, 86-96, 254-263 | regex extraction; missing section → error |
| Per-platform character limits (linkedin 3000, x 280, gbp 1500, facebook 63000, instagram 2200) | **AC11** | 42-48, 265-273 | error includes character count and trim suggestion |

**Mapping summary requested in prompt:**
- **AC1** = required-field, frontmatter-present, id pattern, publish_at, platforms, status (basic schema validators, lines 161-213)
- **AC5** = `publish_at` timezone-offset enforcement (`PUBLISH_AT_PATTERN`, line 59)
- **AC11** = per-platform copy section presence + per-platform character limits (lines 254-273)

**3. Output format — operator-readable error messages**

Errors prefixed with `<file>: Error: ` to stderr (line 308). Each error string is intentionally verbose with remediation hints. Examples in source:
- Line 184-187: `"'publish_at' must include timezone offset (got: '<x>'). Expected ISO 8601 format: YYYY-MM-DDTHH:MM:SS+HH:MM or Z. Example: 2026-04-01T09:00:00-07:00"`
- Line 199-201: `"unknown platform '<p>' in 'platforms' list. Valid values: <sorted>"`
- Line 268-273: `"'<p>' copy section exceeds character limit. Got <N> characters, limit is <L>. Trim <D> characters from the '# <Header>' section."`

Final summary line on completion: `"<N> error(s) found across <M> file(s)."` (line 315) or `"All <M> file(s) passed validation."` (line 320).

**4. CI gate**

Yes — `.github/workflows/validate-pr.yml` lines 33-49 (primary job) and 84-110 (fallback):
- Primary: `echo "$CHANGED_FILES" | xargs python scripts/validate-post.py` (line 49)
- Fallback: per-file loop with `FAILED=1` accumulator (lines 99-110)
- Triggered on PR to `main` when `brands/**/calendar/**/*.md` changes (paths, line 12)

Comment header (lines 3-6) lists the AC refs the workflow gates: AC1, AC5, AC11, AC12 ("ensures only valid docs reach main"), AC-OQ2, AC-OQ3.

**5. AC refs**

In source: AC1, AC5, AC8, AC11, AC-OQ2, AC-OQ3 (docstring + inline). AC12 comes via the workflow header (validate-pr.yml line 6) but is not cited inside the script itself.

---

## Cross-Cutting Patterns

1. **CLI convention is inconsistent across the 3 scripts.**
   - `ghl_social.py` uses `argparse` with subcommands.
   - `validate-brand.py` and `validate-post.py` use raw `sys.argv` with manual flag parsing.
   - All three use `sys.exit(0|1)` with errors to stderr.

2. **AC mapping pattern.** Follows Common Pattern: **CP-1 (AC Namespace Divergence)** — see Phase1_Common.md. Pass-03-specific evidence:
   - `validate-post.py` puts AC tags in the **module docstring** (line 3) and inline comments (lines 125, 179, 205, 215, 253).
   - `validate-brand.py` puts AC tags only in the **module docstring** (line 3) and one inline comment (line 125).
   - `ghl_social.py` has **no AC tags** at all.
   - The workflow `validate-pr.yml` header (lines 5-6) duplicates/extends the per-script AC list and adds AC12 + AC-OQ2/3 framing.
   - AC8 split: `validate-brand.py` AC8 = "raw tokens"; `validate-post.py` AC8 = "required fields, status, author/account resolution." Same token, different rules.

3. **Validation primitives are NOT shared between `validate-brand.py` and `validate-post.py`.** Connects to **CP-8 (Schema Field vs Code Validator Coverage Mismatch)** — see Phase1_Common.md.
   - Both define their own `VALID_PLATFORMS = {"facebook","linkedin","gbp","x","instagram"}` (validate-brand.py:22, validate-post.py:34) — duplicated literal.
   - Both define their own YAML-loading + frontmatter-parsing logic.
   - Neither imports from `publisher/` (except `ghl_social.py`, which imports `GHLAdapter`).
   - `validate-post.py` has its own `parse_frontmatter()` (lines 69-82); `publisher/state.py` per Pass 0 also handles frontmatter — REVIEW (Pass 01) for duplication.

4. **Stale-doc cross-references.** Follows Common Pattern: **CP-2 (Stale-Doc Script-Path References)** — see Phase1_Common.md. Pass-03-specific evidence:
   - `AC_VERIFICATION_SUMMARY.md`'s 4 missing `ghl_social_*.py` script references are now subcommands of `ghl_social.py` — see Subcommand Inventory above.
   - **Newly surfaced:** `validate-post.py` line 251 still tells the operator to `run ghl_social_list_accounts.py` — that script no longer exists; should read `ghl_social.py accounts`. Stale error string.

5. **Dry-run convention.** `ghl_social.py create/delete` use `--dry-run` to mean "no API call." `validate-post.py` accepts `--dry-run` as a no-op alias purely for CLI consistency (line 16). `validate-brand.py` has no dry-run flag.

6. **Schema enum drift between scripts.** Follows Common Pattern: **CP-3 (Status-Lifecycle Drift Cluster)** — see Phase1_Common.md. Pass-03-specific evidence: `validate-post.py` `VALID_STATUSES = {draft, ready, scheduled, published, failed, deferred, video-pending}` (lines 35-37) — **missing `ghl-pending`** vs `models.py:VALID_STATUSES`. `ghl_social.py posts --status` choices = `{scheduled, published, failed, draft}` (line 320) — narrower still.

7. **Two-gate Gate 1 implementation (CI side).** Follows Common Pattern: **CP-4 (Two-Gate Workflow Implementation)** — see Phase1_Common.md. Pass-03-specific evidence: `validate-pr.yml` (Job 1 + Job 2 fallback) runs `validate-post.py` + `validate-brand.py` as the merge-blocking check on PRs that touch `brands/**/calendar/**/*.md` or `brands/**/brand.yaml`. Branch-protection assumed.

---

## Unknowns / Ambiguities

1. **`publish_posts.py`** — cited by `AC_VERIFICATION_SUMMARY.md`, not present, not a `ghl_social.py` subcommand. UNKNOWN whether deleted, never-existed, or intended as the publisher entry point referenced by Pass 0 (`publisher/publisher.py` invoked by `publish.yml`).
2. **GHL endpoint surface for `accounts` and `posts` subcommands** — `cmd_accounts` calls `adapter.get_accounts()`, `cmd_posts` calls `adapter.list_posts(filters)`. Endpoints not visible in this pass; Pass 02 (`ghl.py`).
3. **KV secret-name positive-format validator absent.** `validate-brand.py` only rejects values that *look like* raw tokens; it doesn't enforce the `kv-<brand>-<platform>-token` shape. UNKNOWN whether this is by design (allow any non-token string) or a gap.
4. **`ghl.accounts` block validation.** `validate-brand.py` doesn't check the `ghl` block at all; `validate-post.py` reads `brand.yaml` for `ghl.accounts` cross-validation but **silently passes** when the block is missing (lines 232-234). UNKNOWN whether the eventual `account_ids must be filled in before publishing goes live` launch-blocker (Pass 0 unknown #9) is enforced anywhere; Pass 01 / Pass 04 may resolve.
5. **AC8 split between scripts.** `validate-brand.py` cites AC8 = "raw tokens." `validate-post.py` cites AC8 = "required fields, status, author/account resolution, --dry-run consistency." Same AC label, materially different rules. Pass 06 must reconcile against the canonical AC list.
6. **AC12 attribution.** `validate-pr.yml` cites AC12 ("ensures only valid docs reach main") but no script in this pass cites AC12. Per Pass 0 namespace conflict, AC12 is in the wider namespace not in `AC_VERIFICATION_SUMMARY.md`. Pass 06.
7. **`extract_copy_sections` regex (validate-post.py:88)** uses `^# (.+)\n` — would also match `## ` (no, it's anchored to `^# `, single hash + space). Not flagged but worth noting that section headers must be exactly `# LinkedIn Version` etc. (H1, not H2). Schema (Pass 04) confirms header convention.
8. **`ghl_mode: true` default (validate-post.py:218)** — value defaults true if absent in frontmatter. UNKNOWN whether the schema declares it required or this default is the source of truth.
