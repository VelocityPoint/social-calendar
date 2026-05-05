# Phase 1 — Pass 02 — Platform Adapters

**Snapshot:** `67d061c`
**Files in scope:** `publisher/adapters/{__init__,base,ghl,facebook,instagram,linkedin,gbp,x_twitter}.py` (8 files, 1,338 LOC)
**Phase 0 reviewer ruling:** Five non-GHL adapters are DEPRECATED per README (`README.md:50–54`). GHL is the Phase 1 active channel.

---

## Headline Findings

1. **GHL adapter exposes 5 callable methods** (`publish`, `auth_check`, `delete`, `get_post`, `list_posts`, `get_accounts`) over **5 distinct GHL Social Planner endpoints** — see § GHL.
2. **Deprecated adapters are NOT pure dead code.** They are:
   - **Imported** at module load via `publisher/adapters/__init__.py` (every import always runs).
   - **Registered** in `ADAPTER_REGISTRY` (`__init__.py:20–26`), keyed by platform slug.
   - **Instantiated** at runtime in TWO call sites of `publisher/publisher.py`:
     - `run_publisher` (cron mode) — `publisher.py:309`, `364`, `370` — instantiates whichever adapter the post's `platforms` list names.
     - `run_auth_check` — `publisher.py:472`, `488`, `491` — invoked by `--auth-check` (the path used by `auth-check.yml`). Iterates every non-empty credential in `brand.credentials` and instantiates that adapter to call `.auth_check()`.
   - **NOT instantiated** in GHL mode (`run_ghl_publisher`, `publisher.py:131–298`) — that path imports `GHLAdapter` directly (`publisher.py:150`, `181`) and bypasses `ADAPTER_REGISTRY` entirely (cf. file docstring `publisher.py:31`: "Uses GHLAdapter exclusively (no per-platform adapter registry lookup)").
3. **Confirms Phase 0 review note 4** (`auth-check.yml` env vars include `FACEBOOK_PAGE_ID`, `LINKEDIN_AUTHOR_URN`, `GBP_LOCATION_NAME`, `INSTAGRAM_USER_ID` because the deprecated adapters' `auth_check` methods are still reached). The publish path (`--mode ghl`) does not reach them.

---

## Base

### `publisher/adapters/base.py` (142 LOC)

**Module docstring (line 1–8):**
> "All platform adapters inherit from BaseAdapter. Defines the interface: publish(), auth_check(), rate_limit_check(). Ref: AC2 (auth_check), AC3/AC4 (publish), AC-OQ6 (rate_limit_check)"

**Class:** `BaseAdapter(ABC)` — abstract base.

**Class attribute:**
- `platform: str` — subclass overrides with platform slug (`"x"`, `"facebook"`, `"linkedin"`, `"instagram"`, `"gbp"`, `"ghl"`).

**`__init__(self, brand: Brand, state_dir: Path)`** — every adapter takes a `Brand` model and a state directory `Path`. Stores `_rate_limit_state: Optional[RateLimitState] = None` (lazy).

**Methods:**

| Method | Signature | Required? | Purpose |
|---|---|---|---|
| `rate_limit_state` (property) | `() -> RateLimitState` | concrete | Lazy-load `RateLimitState.load_or_create(state_dir / "rate_limits", platform)` |
| `save_rate_limit_state` | `() -> None` | concrete | Persist to `state_dir / "rate_limits"` |
| `check_rate_limit` | `(post_id: str) -> bool` | concrete | AC-OQ6 (quoted `:58`: "Check rate limit before any API call. Returns True if allowed, False if deferred"). Logs `[DEFERRED]` on limit. |
| `increment_rate_limit` | `() -> None` | concrete | Increments counter after successful call |
| **`publish`** | `(post: Post, copy_text: str, image_path: Optional[Path] = None) -> str` | **abstractmethod** | Returns platform post ID. Raises `PublishError`/`RateLimitError`/`PermanentError` per docstring. |
| **`auth_check`** | `() -> bool` | **abstractmethod** | AC2. Logs `[AUTH OK] {platform}` or `[AUTH FAIL] {platform}`. |
| `_get_credential` | `(secret_name: str) -> Optional[str]` | concrete | KV-or-env-var resolver (see Cross-Cutting). |

**Auth-probe interface (AC2 / `--auth-check`):**
- Each adapter implements `auth_check() -> bool`.
- Driven by `publisher.publisher.run_auth_check` (`publisher.py:469–496`), which iterates `brand.credentials.__dict__` and instantiates whichever adapter is keyed by the credential field name in `ADAPTER_REGISTRY`.

**Post-shape input:**
- `post: Post` (pydantic model — Pass 01 covers fields).
- `copy_text: str` — pre-extracted, platform-specific copy section.
- `image_path: Optional[Path]` — optional local file path.

**Result shape:**
- Success: `str` — platform post ID. Format varies (tweet ID numeric, LinkedIn URN, GBP `accounts/.../localPosts/...` resource name, GHL post id).
- Errors (defined in `publisher/retry.py`, imported by every adapter):
  - `PublishError` — retryable (5xx, network)
  - `RateLimitError(retry_after=...)` — HTTP 429
  - `PermanentError(status_code=...)` — non-retryable (400/401/403/404)

**Credential resolution (`_get_credential`, lines 110–142):**
1. Tries env var `secret_name.upper().replace("-", "_")` first (Phase 1 fallback / GH Actions environment secrets).
2. Falls back to `az keyvault secret show --vault-name $AZURE_KEY_VAULT_NAME --name $secret_name` via subprocess (Phase 2).
3. Returns `None` and logs `[CREDENTIAL] Could not retrieve secret` if both fail.
- Inline comment (line 117): "Try env var first (Phase 1 fallback, also used in GH Actions environment secrets)"
- Inline comment (line 122): "Try Key Vault via az CLI (Phase 2 — if AZURE_KEY_VAULT_NAME is set)"

---

## GHL (active)

### `publisher/adapters/ghl.py` (341 LOC)

**Module-level constants:**
- `BASE_URL = "https://services.leadconnectorhq.com"` (line 40)
- `API_VERSION = "2021-07-28"` (line 41) — matches the Lead Connector Hub version pattern flagged in Phase 0 cross-spec to RP / sr-ops-tools.

**Module-level exception:**
- `GHLError(Exception)` — `__init__(status_code, message)` — represents 5xx (retryable per docstring; in practice raised only for `>=500` in `_request`, line 338).

### Class `GHLAdapter(BaseAdapter)` — `platform = "ghl"`

**`__init__(brand, state_dir)`** (lines 60–73):
- `self.location_id` resolved from `os.environ["GHL_LOCATION_ID"]` first, then `brand.ghl["location_id"]`, else `""`.
- `self.api_key = os.environ.get("GHL_API_KEY", "")`.
- `self.account_map = brand.ghl["accounts"]` if dict else `{}` — format `{author: {platform: account_id}}`.

### Public surface (full)

| Method | Signature | Endpoint | Verb |
|---|---|---|---|
| `publish` | `(post, copy_text, image_path=None) -> str` | `/social-media-posting/{location_id}/posts` | POST |
| `auth_check` | `() -> bool` | (delegates to `get_accounts`) | GET |
| `delete` | `(ghl_post_id: str) -> bool` | `/social-media-posting/{location_id}/posts/{ghl_post_id}` | DELETE |
| `get_post` | `(ghl_post_id: str) -> Optional[dict]` | `/social-media-posting/{location_id}/posts/{ghl_post_id}` | GET |
| `list_posts` | `(filters: Optional[dict] = None) -> List[dict]` | `/social-media-posting/{location_id}/posts/list` | POST (body filters) |
| `get_accounts` | `() -> List[dict]` | `/social-media-posting/{location_id}/accounts` | GET |

Internal helpers: `_resolve_accounts(author, platform) -> List[str]`; `_request(method, path, body=None) -> requests.Response`.

### GHL endpoint surface (verbatim)

All paths are appended to `BASE_URL` = `https://services.leadconnectorhq.com`. All requests sent through `_request` (lines 282–341).

1. **POST** `/social-media-posting/{location_id}/posts` — create post. Payload (`publish`, lines 116–124):
   ```python
   {
     "accountIds": account_ids,           # List[str] from _resolve_accounts
     "content": copy_text,
     "scheduledAt": post.publish_at,      # ISO 8601 with TZ
     "status": "draft",                   # AC18-style gating; see Draft creation flow below
     "type": "image" if image_url else "text",
     "mediaUrls": [image_url],            # Only present when image_url is truthy
   }
   ```
   Response: parses `data.get("id") or data.get("post_id")`. Raises `PublishError` if neither present.

2. **DELETE** `/social-media-posting/{location_id}/posts/{ghl_post_id}` — `delete()`, lines 180–187. Treats both 200 and 204 as success.

3. **GET** `/social-media-posting/{location_id}/posts/{ghl_post_id}` — `get_post()`, lines 196–213. Returns `None` on 404 (via `PermanentError` swallow OR `GHLError` swallow — defensive double-handling).

4. **POST** `/social-media-posting/{location_id}/posts/list` — `list_posts()`, lines 228–236. Body is the `filters` dict. Parses `data` if list; else `data["posts"]` or `data["data"]`.

5. **GET** `/social-media-posting/{location_id}/accounts` — `get_accounts()`, lines 245–251. Doubles as the auth-check probe.

### Auth (Bearer + version header)

`_request` builds (lines 305–311):
```python
headers = {
    "Authorization": f"Bearer {self.api_key}",
    "Version": "2021-07-28",
    "Content-Type": "application/json",
    "Accept": "application/json",
}
```
- Bearer token from `GHL_API_KEY` env var (set in `__init__`, line 69).
- `Version` header value `"2021-07-28"` matches the pattern Phase 0 flagged for cross-spec relevance to RP / sr-ops-tools (Pass 02 confirms identical convention).
- Timeout fixed at 30s (line 319).

### Account resolution from brand.yaml

`_resolve_accounts(author, platform)` (lines 257–280):
- `account_map` shape per docstring (lines 51–55): `{author: {platform: account_id}}`. Example: `{"dave": {"linkedin": "acc_123", "facebook": "acc_456"}}`.
- Lookup chain:
  1. If `author is None/empty` → `PermanentError("No author specified for platform {platform}")`.
  2. If `author not in self.account_map` → `PermanentError("Unknown author: {author}")`.
  3. If `platform not in account_map[author]` → `PermanentError("No GHL account configured for author={author} platform={platform}")`.
  4. Else returns `[account_map[author][platform]]` — single-element list (one account per platform per author at this snapshot).
- Note: `publish` picks `platform = post.platforms[0] if post.platforms else "unknown"` (line 105) — only the first platform in the post's list is used per call.
- **Cross-ref Daedalus design**: Pass 04 will resolve actual brand.yaml `ghl.accounts` shape; here we record only the adapter-side contract.

### Draft creation flow

The `"status": "draft"` literal is hardcoded in the payload (line 120). Inline comment quotes:
> "Gate 2: land as draft for Dave's manual approval in GHL UI"

This implements the 2-gate workflow: GHL post is created as draft; Dave approves visually in GHL Social Planner UI. The adapter does **not** support a non-draft status — there is no flag/parameter to override.

### Error handling matrix (`_request`, lines 313–341)

| Path | Status | Action |
|---|---|---|
| `requests.exceptions.RequestException` | network | raise `PublishError(f"GHL network error: {e}")` |
| HTTP 429 | rate limit | parse `Retry-After` (default 60) → raise `RateLimitError(..., retry_after=retry_after)` |
| HTTP 400/401/403/404 | client | raise `PermanentError(f"GHL {status}: {body[:500]}", status_code=status)` |
| HTTP >= 500 | server | raise `GHLError(status, body[:500])` |
| 2xx/3xx | success | log debug + return `Response` |

`auth_check` (lines 141–160) catches three classes — `GHLError`, `PermanentError`, `Exception` — and returns `False` on any. Returns `True` only after a successful `get_accounts()` call.

`publish` adds upstream rate-limit gate (line 101): `if not self.check_rate_limit(post.id): raise PublishError("Publish deferred — rate limit exceeded for {post.id}")`.

### AC references (verbatim from file)

- Module docstring (line 11): "Ref: AC3 (text publish), AC4 (image publish), AC6 (list accounts)"
- `auth_check` docstring (line 143): "AC2: Verify GHL API authentication by listing connected accounts."

(No in-file AC18 reference — the "draft" status is annotated as "Gate 2" in code without an AC number. Cross-spec to Pass 06 AC reconciliation.)

---

## Deprecated Adapters

**Deprecation marker convention:** None of the 5 deprecated adapter files contain the literal string `DEPRECATED` or `deprecated` (verified via grep). The deprecation is asserted **only in `README.md` lines 50–54** (verbatim):

```
facebook.py         -- Deprecated (GHL handles Meta OAuth)
instagram.py        -- Deprecated
linkedin.py         -- Deprecated
x_twitter.py        -- Deprecated
gbp.py              -- Deprecated
```

Several files instead carry the comment "Phase 1 skeleton" — for example `facebook.py:4` ("Phase 1 skeleton. Interface is complete; full API integration pending credential setup."), `linkedin.py:4`, `gbp.py:4`. **`instagram.py` and `x_twitter.py` carry no skeleton/deprecation marker in-file.**

**Runtime status (CONFIRMED):** Imported + registered in `ADAPTER_REGISTRY` + instantiated by `run_publisher` (cron) and `run_auth_check`. NOT instantiated in `--mode ghl`.

**Tests reference (Pass 05 will confirm):** Grep across `tests/` for `FacebookAdapter|InstagramAdapter|LinkedInAdapter|GBPAdapter|XTwitterAdapter` — **zero matches**. Both test files reference only `GHLAdapter` / `publisher.adapters.ghl`. The deprecated adapters have NO test coverage at this snapshot.

### `facebook.py` (126 LOC)

- **Marker:** `facebook.py:4` "Phase 1 skeleton. Interface is complete; full API integration pending credential setup."
- **AC refs (line 6):** "AC3 (text publish), AC4 (image publish), AC13 (token refresh), AC14 (shared Meta creds)"
- **Class:** `FacebookAdapter(BaseAdapter)` — `platform = "facebook"`.
- **Auth:** Bearer-style page access token from KV via `brand.credentials.get_kv_secret_name("facebook")` + `_get_credential`. Page ID from env var `FACEBOOK_PAGE_ID`.
- **API base:** `GRAPH_API_BASE = "https://graph.facebook.com/v19.0"`.
- **Public methods:** `auth_check()` (GET `/{page_id}?fields=id,name`); `publish(post, copy_text, image_path=None) -> str`.
- **Internal methods:** `_get_page_access_token`, `_get_page_id`, `_publish_text` (POST `/{page_id}/feed`), `_publish_with_photo` (POST `/{page_id}/photos`, multipart), `_raise_for_status`.

### `instagram.py` (167 LOC)

- **Marker:** No in-file deprecation/skeleton notice. README-only.
- **AC refs (line 7–8):** "AC14 (shared Meta creds — must only read facebook.json / facebook KV secret), AC3 (text publish), AC4 (image publish — Instagram requires media URL, not file upload)"
- **Class:** `InstagramAdapter(BaseAdapter)` — `platform = "instagram"`.
- **Auth (AC14 invariant):** Uses `brand.credentials.get_kv_secret_name("facebook")` — must NOT read a separate instagram credential. Parses returned blob as JSON, extracts `instagram_user_id` + `instagram_access_token` (or falls back to `INSTAGRAM_USER_ID` env / `page_access_token`).
- **API base:** Same `GRAPH_API_BASE` as facebook.
- **Public methods:** `auth_check()` (GET `/{ig_user_id}?fields=id,username`); `publish(post, copy_text, image_path=None) -> str`.
- **Internal methods:** `_get_credentials -> (str, str)`, `_get_public_image_url`, `_create_image_container` (POST `/{user_id}/media`), `_create_text_container` (raises `PermanentError` — Instagram has no text-only API), `_publish_container` (POST `/{user_id}/media_publish`), `_raise_for_status`.

### `linkedin.py` (183 LOC)

- **Marker:** `linkedin.py:4` "Phase 1 skeleton. Interface complete; full integration pending credential setup."
- **AC refs (line 6):** "AC3 (text publish <= 3000 chars), AC4 (image publish), AC13 (OAuth token refresh)"
- **Class:** `LinkedInAdapter(BaseAdapter)` — `platform = "linkedin"`.
- **Auth:** Bearer token from `brand.credentials.get_kv_secret_name("linkedin")`. Author URN from env var `LINKEDIN_AUTHOR_URN`. Hard char limit `LINKEDIN_CHAR_LIMIT = 3000`.
- **API base:** `LINKEDIN_API_BASE = "https://api.linkedin.com/v2"`. Header `LinkedIn-Version: 202401` on auth probe.
- **Public methods:** `auth_check()` (GET `/rest/organizationAcls?q=roleAssignee`); `publish(post, copy_text, image_path=None) -> str`.
- **Internal methods:** `_get_token`, `_get_author_urn`, `_publish_text` (POST `/ugcPosts`, `lifecycleState=PUBLISHED`, `shareMediaCategory=NONE`), `_publish_with_image` (3-step: register-upload → PUT image → POST `/ugcPosts` with `IMAGE`), `_raise_for_status`.

### `gbp.py` (146 LOC)

- **Marker:** `gbp.py:4` "Phase 1 skeleton. Interface complete; full integration pending credential setup."
- **AC refs (line 6–7):** "AC3 (text publish <= 1500 chars), AC4 (image/photo posts), AC13 (OAuth token refresh via Google), AC-OQ6 (rate limit)"
- **Class:** `GBPAdapter(BaseAdapter)` — `platform = "gbp"`.
- **Auth:** OAuth `access_token` (parsed from JSON blob in KV via `get_kv_secret_name("gbp")`, or raw token if not JSON). Location resource name from env var `GBP_LOCATION_NAME` (format `accounts/{a}/locations/{l}`). Char limit `GBP_CHAR_LIMIT = 1500`.
- **API base:** `GBP_API_BASE = "https://mybusiness.googleapis.com/v4"`.
- **Public methods:** `auth_check()` (GET `https://oauth2.googleapis.com/tokeninfo?access_token=...`); `publish(post, copy_text, image_path=None) -> str`.
- **Internal methods:** `_get_credentials -> dict`, `_get_access_token`, `_get_location_name`, `_get_public_image_url`, `_raise_for_status`. `publish` POSTs `{GBP_API_BASE}/{location_name}/localPosts` with `summary`, `topicType: STANDARD`, optional `media[].sourceUrl`.

### `x_twitter.py` (204 LOC)

- **Marker:** No in-file deprecation/skeleton notice. README-only.
- **AC refs (line 7–8):** "AC15 (xurl subprocess, no direct HTTP), AC3 (text publish), AC4 (image publish), AC-OQ4 (retry via publisher/retry.py), AC-OQ6 (rate limit)"
- **Class:** `XTwitterAdapter(BaseAdapter)` — `platform = "x"`. Char limit `X_CHAR_LIMIT = 280`.
- **Auth (AC15 — distinct from all others):** Shells out to `xurl` CLI via `subprocess.run`. NO HTTP imports of `api.twitter.com` / `api.x.com`; NO Twitter SDK. Inline comment line 3: "Uses xurl as a subprocess. No direct HTTP calls to api.twitter.com or api.x.com. No Twitter/X SDK imports."
- **Public methods:** `auth_check()` (`xurl whoami`, exit 0 = OK); `publish(post, copy_text, image_path=None) -> str`.
- **Internal methods:** `_upload_media(image_path) -> str` (`xurl media upload <path>`), `_raise_for_xurl_error` (maps stderr substrings `"429"/"rate limit"`, `"401"/"unauthorized"/"forbidden"`, `"400"/"bad request"` to `RateLimitError`/`PermanentError(401)`/`PermanentError(400)`), `_parse_tweet_id`, `_parse_media_id` (both: try JSON `id`/`id_str`/`tweet_id`/`media_id`/`media_id_string` keys, then regex `\b(\d{10,})\b`).
- Pre-flight `shutil.which("xurl")` guard in both `auth_check` (returns False if missing) and `publish` (raises `PermanentError`).
- **Resolves Phase 0 unknown #3:** `xurl` IS shelled out as a subprocess; the `kv-secondring-x-config` JSON is `xurl`'s own config file (consumed by the CLI tool's auth, NOT parsed by this adapter).

---

## Cross-Cutting Patterns

### CC-PA1: BaseAdapter interface conformance — all 6 adapters honor it

Every adapter defines `platform: str`, inherits `BaseAdapter`, implements abstract `publish` and `auth_check`. Even deprecated adapters honor the contract — no skipping/stubbing. This is what makes them runtime-loadable for `--auth-check`.

### CC-PA2: Per-platform auth mechanism is the largest divergence

| Adapter | Auth mechanism | Auth probe |
|---|---|---|
| GHL | Bearer + `Version: 2021-07-28` header | GET `/social-media-posting/{loc}/accounts` |
| Facebook | Page access token (query-string `access_token=`) | GET `/{page_id}?fields=id,name` |
| Instagram | Same Meta credential as facebook (AC14) — JSON blob with `instagram_user_id` + `instagram_access_token` | GET `/{ig_user_id}?fields=id,username` |
| LinkedIn | OAuth Bearer + `LinkedIn-Version: 202401` + `X-Restli-Protocol-Version: 2.0.0` (on writes) | GET `/rest/organizationAcls?q=roleAssignee` |
| GBP | Google OAuth Bearer | GET `https://oauth2.googleapis.com/tokeninfo` (Google tokeninfo endpoint, not the API itself) |
| X/Twitter | `xurl` CLI subprocess (AC15) — no in-process HTTP | `xurl whoami` exit-0 |

Each maps a different KV secret name via `brand.credentials.get_kv_secret_name(platform)` (Pass 01 covers `Brand.credentials`).

### CC-PA3: Credential resolution chain (env-first, KV-fallback)

`BaseAdapter._get_credential` (`base.py:110–142`) is the single shared resolver. Order: env var (uppercased, dashes-to-underscores) → `az keyvault secret show` if `AZURE_KEY_VAULT_NAME` is set → `None`. Used by all adapters except GHL (which reads `GHL_API_KEY` directly from env, line 69) and X (which delegates auth entirely to `xurl`).

### CC-PA4: Error-type mapping pattern (HTTP → typed exception)

Every HTTP-using adapter uses the same shape: 200/201 OK → return; 429 → `RateLimitError(retry_after)`; 400/403 → `PermanentError(status_code)`; everything else → `PublishError(status_code)`. GHL adds 401/404 to the `PermanentError` bucket and 5xx to the bespoke `GHLError`. X/Twitter does string-matching on stderr instead of HTTP codes.

### CC-PA5: Image-handling strategies diverge

| Strategy | Adapters |
|---|---|
| Multipart file upload | Facebook (`/photos`) |
| 3-step register-upload + PUT + post | LinkedIn |
| 2-step container + media_publish via PUBLIC URL | Instagram |
| `sourceUrl` (public URL) inline | GBP |
| URL-only (no upload) | GHL (`mediaUrls: [url]`) |
| Subprocess upload + media_id | X (`xurl media upload`) |
| Public URL prerequisite via `ASSETS_BASE_URL` env var | Instagram, GBP |

### CC-PA6: AC-reference convention

Follows Common Pattern: **CP-1 (AC Namespace Divergence)** — see Phase1_Common.md. Pass-02-specific evidence: ACs are cited only in module docstrings (top of each file), not on individual methods (except `auth_check` carries `AC2:` / `AC-OQ6:` inline). AC15 is unique to `x_twitter.py`; AC14 is unique to `instagram.py` (cross-refs facebook). AC18 is **not referenced** anywhere in adapters despite Pass 02 prompt suggesting it for the GHL "draft" status enforcement — see Unknowns.

### CC-PA7: Deprecation marker convention is informal

Follows Common Pattern: **CP-7 (Deprecated-Adapter Runtime Liveness)** — see Phase1_Common.md. Pass-02-specific evidence: deprecation is asserted only in README. In-file markers vary: 3 of 5 deprecated adapters say "Phase 1 skeleton" (facebook/linkedin/gbp); 2 (instagram/x_twitter) carry no in-file marker at all. No file uses the word "deprecated" inline. Imported, registered in `ADAPTER_REGISTRY`, and instantiated by both `run_publisher` (cron) and `run_auth_check`. Zero tests reference the 5 deprecated adapter classes.

### CC-PA8: ADAPTER_REGISTRY is the platform→class router; GHL bypasses it

`ADAPTER_REGISTRY` (`__init__.py:20–26`) is `dict[str, type[BaseAdapter]]` keyed `"x"|"facebook"|"instagram"|"linkedin"|"gbp"`. **GHLAdapter is intentionally excluded.** Instead, `__init__.py:29` exports `GHL_ADAPTER_CLASS = GHLAdapter` as a separate single-class reference. This is the structural mechanism enforcing "GHL mode bypasses per-platform dispatch."

### CC-PA9: GHL_LOCATION_ID resolution

`GHLAdapter.__init__` resolves location id with **env-var-first priority**: `os.environ["GHL_LOCATION_ID"]` → `brand.ghl["location_id"]` → `""` (empty). This means CI/workflow secret can override brand.yaml. (Cross-ref to `sr-ops-tools` Pass 04 reference of the same `cUgvqrKmBM4sAZvMH1JS` ID is brand.yaml-side — Pass 04 will verify.) Connects to **CP-9 (Hardcoded Constants & Conventions)** — see Phase1_Common.md.

### CC-PA10: Two-gate Gate 2 wire-level enforcement

Follows Common Pattern: **CP-4 (Two-Gate Workflow Implementation)** — see Phase1_Common.md. Pass-02-specific evidence: `GHLAdapter.publish` hardcodes `"status": "draft"` in the API payload (ghl.py:120). Inline comment: "Gate 2: land as draft for Dave's manual approval in GHL UI." No flag/parameter overrides this. Cross-cuts CP-9 (hardcoded payload literal).

### CC-PA11: Cross-spec GHL convention

Follows Common Pattern: **CP-11 (Cross-Spec GHL Convention)** — see Phase1_Common.md. Pass-02-specific evidence: `BASE_URL = "https://services.leadconnectorhq.com"` (ghl.py:40) + `API_VERSION = "2021-07-28"` (ghl.py:41) + Bearer token convention (ghl.py:305-311). Identical convention to RP and sr-ops-tools per Phase 0 cross-spec markers.

---

## Unknowns / Ambiguities

1. **AC18 not referenced in adapters.** Pass 02 prompt asked whether `status: "draft"` is AC18-tied. Source of truth not in adapters; in-code annotation calls it "Gate 2" without an AC number. **→ Pass 06 (AC reconciliation).**
2. **`get_post` swallows 404 from BOTH `PermanentError` and `GHLError`** (lines 204–213). `_request` only raises `PermanentError(404)` — never `GHLError(404)` (that path is gated by `>= 500`). Defensive double-handling, but the `GHLError` branch appears unreachable. UNKNOWN whether intentional or dead code. **→ flag for Pass 06.**
3. **`publish` uses only `post.platforms[0]`** (line 105) for account resolution, but `accountIds` is plural. Whether multi-platform single-call is supported by the API or a future-feature placeholder — UNKNOWN from this code alone. **→ Pass 04 (brand.yaml shape) + Daedalus design doc reference.**
4. **`scheduledAt` semantics with `status: draft`** — whether GHL honors `scheduledAt` for draft posts or treats it as advisory. Inline comment (line 119) calls it "preserved for GHL reference." **→ external GHL API; out of scope.**
5. **`brand.ghl` attribute** — `getattr(brand, "ghl", None)` (line 63). UNKNOWN whether `Brand` model defines `ghl` formally or via dynamic dict (`isinstance(ghl_cfg, dict)` checks suggest it may be untyped). **→ Pass 01 (publisher/models.py) verifies.**
6. **`X-config` JSON content** — `x_twitter.py` does not reference `kv-secondring-x-config` directly; the adapter relies on `xurl`'s own config-file mechanism. The brand.yaml comment about the JSON shape is informational about `xurl`'s own format. RESOLVED: not parsed in this repo. **→ Phase 0 unknown #3 closed.**
7. **5 deprecated adapters' instantiation in `--auth-check`** — RESOLVED: yes, via `run_auth_check` → `ADAPTER_REGISTRY`. They are not pure dead code. **→ Phase 0 unknown #4 closed.**
8. **No adapter tests for deprecated 5** — confirmed zero references in `tests/`. Whether this is acceptable or a coverage gap is a Pass 05 question.
