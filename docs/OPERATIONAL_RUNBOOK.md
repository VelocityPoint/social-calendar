# Operational Runbook — GHL Social Planner Pipeline

**Issue:** [VelocityPoint/social-calendar#2](https://github.com/VelocityPoint/social-calendar/issues/2)
**Audience:** Operators managing the live social publishing pipeline
**Sub-account:** [SR] Sales (`cUgvqrKmBM4sAZvMH1JS`)

---

## 1. System Health Overview

### Normal State

A healthy pipeline looks like this:
- `publish.yml` Actions workflow: ✅ green on recent pushes
- `validate-pr.yml`: ✅ green on open PRs with post files
- `auth-check.yml`: ✅ green on weekly run
- Post files in `brands/secondring/calendar/`: `status: scheduled` or `status: published`
- No files stuck at `status: ready` without a corresponding `ghl_post_id`

### Degraded State Indicators

| Indicator | Likely Issue |
|-----------|-------------|
| `publish.yml` failing on every push | Auth error (expired API key) or code bug |
| Post files stuck at `status: ready` after merge | Publisher didn't run or failed silently |
| `auth-check.yml` failing | GHL API key expired or wrong scope |
| Posts with `status: failed` and no retry | Permanent error — needs manual intervention |
| No Actions runs for > 24 hours after content merges | Trigger misconfiguration |

---

## 2. Monitoring Setup

### GitHub Actions (primary monitoring)

The pipeline runs entirely in GitHub Actions. Monitor at:
```
https://github.com/VelocityPoint/social-calendar/actions
```

**Key workflows to watch:**
- `Social Calendar Publisher` (`publish.yml`) — triggers on every merge
- `Validate PR` (`validate-pr.yml`) — triggers on every PR
- `Auth Check` (`auth-check.yml`) — weekly

**Enable email notifications:**
- GitHub > Settings > Notifications > Actions > "Failed workflows only"

### GHL Social Planner UI (secondary monitoring)

- Log into GHL > [SR] Sales > Marketing > Social Planner
- Check "Scheduled" tab for upcoming posts
- Check "Failed" tab if posts aren't going out

### Detecting Failed Posts in the Repo

```bash
cd ~/workspace/repos/VelocityPoint/social-calendar
git pull origin main

# Find all failed posts
grep -rl "status: failed" brands/*/calendar/ 2>/dev/null

# Find all ready posts that should have been published but weren't
grep -rl "status: ready" brands/*/calendar/ 2>/dev/null
```

---

## 3. Alerting Setup

### Current State (Phase 1)

Phase 1 does not have automated alerting beyond GitHub email notifications. The `retry.py` module has hooks for GitHub issue creation on persistent failures (`AC7`).

### Manual Alert Check Procedure

Run this after any suspicious publish.yml failure:

```bash
# Check last 10 publish workflow runs
gh run list --repo VelocityPoint/social-calendar --workflow=publish.yml --limit 10

# View a specific failed run
gh run view <run-id> --repo VelocityPoint/social-calendar --log-failed
```

### Phase 2 Alerting (planned)

- Telegram notification to Dave on `status: failed` posts (via `retry.py` GitHub issue creation + issue-to-Telegram bridge)
- Daily summary of posts scheduled/published/failed

---

## 4. Incident Response Procedures

### P0 — All Publishing Stopped

**Symptoms:** Multiple posts with `status: failed` or `status: ready` (never processed), `publish.yml` consistently failing.

**Runbook:**

1. **Check GitHub Actions for error details:**
   ```bash
   gh run list --repo VelocityPoint/social-calendar --workflow=publish.yml --limit 5
   gh run view <latest-run-id> --repo VelocityPoint/social-calendar --log-failed
   ```

2. **Test GHL API key validity:**
   ```bash
   export GHL_API_KEY="<key from GitHub secrets>"
   export GHL_LOCATION_ID="cUgvqrKmBM4sAZvMH1JS"
   python scripts/ghl_social_list_accounts.py
   ```
   - If `401`: key expired → see **API Key Rotation** (Section 6)
   - If `200`: key valid → check publisher code

3. **If key is valid, run publisher manually in dry-run:**
   ```bash
   python -m publisher.publisher --mode ghl --brand secondring --dry-run
   ```
   Look for Python exceptions or validation errors.

4. **Re-trigger the workflow manually:**
   ```bash
   gh workflow run publish.yml --repo VelocityPoint/social-calendar \
     -f brand=secondring -f dry_run=false
   ```

5. **If still failing:** Check for recent code changes in `publisher/`. Roll back the last merged PR if the issue correlates with a code change.

---

### P1 — Individual Post Failed

**Symptoms:** One or more post files have `status: failed` and an `error:` field.

**Runbook:**

1. **Identify the failed post(s):**
   ```bash
   grep -rl "status: failed" brands/ | sort
   ```

2. **Read the error:**
   ```bash
   head -20 brands/secondring/calendar/2026/04/2026-04-09-facebook.md
   # Look for: error: "..."
   ```

3. **Triage by error type:**

   | Error | Action |
   |-------|--------|
   | `No GHL account for dave/linkedin` | Fix `brand.yaml` account mapping (see Section 5) |
   | `GHL Error 401` | Rotate API key (see Section 6) |
   | `GHL Error 429: Rate limit` | Wait for rate limit window; re-queue post |
   | `GHL Error 500` | Transient; reset post to `draft` and re-queue |
   | `PermanentError: Invalid platform` | Schema bug; fix post file |

4. **Reset and re-queue the post:**
   ```bash
   # Edit the post file
   # Change: status: failed → status: draft
   # Remove: error: "..."
   # Remove: ghl_post_id (if present — means partial state)

   git add brands/secondring/calendar/2026/04/2026-04-09-facebook.md
   git commit -m "fix: reset failed post for re-publish [Ref #2]"
   git push
   # Open PR → Dave sets status: ready → merge → re-publishes
   ```

---

### P2 — Post Published at Wrong Time

**Symptoms:** Post went out earlier or later than `publish_at`.

**Cause:** GHL scheduling is generally accurate to within a few minutes. Significant drift suggests the `scheduledAt` value in the API payload was wrong.

**Runbook:**
1. Check the `ghl_post_id` on the post file
2. In GHL UI: find the post and check its scheduled time
3. Compare `publish_at` in the file to what was sent in the API payload
4. If post is live and wrong: must be deleted directly on-platform (LinkedIn, Facebook, etc.) — GHL cannot recall live posts
5. If post is still scheduled (wrong future time): use `ghl_social_delete_post.py` and create a new post

---

### P3 — Duplicate Post Published

**Symptoms:** Same content appeared twice on a platform.

**Cause:** Publisher ran twice on the same `status: ready` file (shouldn't happen due to idempotency guard, but possible if `ghl_post_id` write-back failed).

**Runbook:**
1. Find the duplicate GHL post IDs (list via `ghl_social_list_posts.py`)
2. Delete the duplicate: `python scripts/ghl_social_delete_post.py --post-id <duplicate-id>`
3. Check the post file for `ghl_post_id` — if missing, the write-back failed
4. Manually add `ghl_post_id` and `status: scheduled` to prevent re-publish

---

## 5. Social Account Connection Troubleshooting

### Check Connection Status

```bash
python scripts/ghl_social_list_accounts.py
```

Healthy output includes accounts with `STATUS: connected`. If an account shows `disconnected` or doesn't appear, it needs reconnection.

### Reconnecting a Social Account

Social account OAuth connections can expire (especially Twitter/X and Instagram). When a connection drops, posts to that platform will fail with a `PermanentError` from GHL.

**Reconnection procedure:**
1. Log into GHL > [SR] Sales sub-account
2. Marketing > Social Planner
3. Click the platform icon that shows as disconnected
4. Re-authorize the OAuth flow (will redirect to the platform's OAuth consent page)
5. After reconnection, verify: `python scripts/ghl_social_list_accounts.py`
6. Note: The GHL account ID **may change** after reconnection. If it does, update `brand.yaml`:
   ```bash
   python scripts/ghl_social_list_accounts.py
   # Copy the new account ID
   # Edit brands/secondring/brand.yaml → ghl.accounts.dave.<platform>: "<new_id>"
   # Open PR → merge
   ```

### Platform-Specific OAuth Notes

| Platform | Token lifetime | Reconnection notes |
|----------|---------------|-------------------|
| **Facebook** | Long-lived page tokens (60 days, auto-refreshed by GHL) | Rare expirations; usually stable |
| **Instagram** | Shared with Facebook app | Reconnects when Facebook reconnects |
| **LinkedIn** | 60-day tokens | May expire; more frequent reconnection needed |
| **Google Business Profile** | OAuth refresh tokens | Stable; only breaks if Google revokes access |
| **Twitter/X** | API key + app tokens | Most fragile; monitor closely |

---

## 6. API Key Rotation Procedures

### When to Rotate

- `auth-check.yml` workflow reports 401 error
- GHL admin rotates all keys (security incident)
- Key was accidentally exposed in logs or commits

### Generating a New GHL API Key

1. Log into GHL
2. Switch to [SR] Sales sub-account (`cUgvqrKmBM4sAZvMH1JS`)
3. Settings > API Keys > Create New Key
4. **Required scopes:** `social-media-posting.*` (at minimum: `social-media-posting.read`, `social-media-posting.write`)
5. Copy the new key immediately (shown only once)

### Updating the GitHub Secret

```bash
# Via GitHub CLI
gh secret set GHL_API_KEY --repo VelocityPoint/social-calendar

# Enter the new key when prompted
```

Or via GitHub UI:
- VelocityPoint/social-calendar > Settings > Secrets and variables > Actions
- `GHL_API_KEY` > Update

### Verifying the New Key

```bash
export GHL_API_KEY="<new-key>"
export GHL_LOCATION_ID="cUgvqrKmBM4sAZvMH1JS"
python scripts/ghl_social_list_accounts.py
# Should return account list without errors
```

### Deactivating the Old Key

After confirming the new key works:
1. GHL > [SR] Sales > Settings > API Keys
2. Find the old key and deactivate/delete it

---

## 7. Going Live Checklist (First-Time Setup)

Before the pipeline can publish live posts, the following must be true:

- [ ] **Social accounts connected in GHL**
  - GHL > [SR] Sales > Marketing > Social Planner > Connect Accounts
  - Connect: LinkedIn, Facebook, Instagram, Google Business Profile

- [ ] **Account IDs discovered**
  ```bash
  python scripts/ghl_social_list_accounts.py
  ```

- [ ] **brand.yaml updated** with real account IDs
  - Replace `"<account_id>"` placeholders in `brands/secondring/brand.yaml`
  - Open PR → merge

- [ ] **GitHub secrets set**
  | Secret | Value |
  |--------|-------|
  | `GHL_API_KEY` | GHL Bearer token with `social-media-posting` scope |
  | `GHL_LOCATION_ID` | `cUgvqrKmBM4sAZvMH1JS` |

- [ ] **Dry-run passes**
  ```bash
  python -m publisher.publisher --mode ghl --brand secondring --dry-run
  ```

- [ ] **Live E2E test passed**
  1. Create test post via `ghl_social_create_post.py`
  2. Verify it appears in `ghl_social_list_posts.py`
  3. Delete it via `ghl_social_delete_post.py`

---

## 8. Scheduled Maintenance

### Weekly

- Review `auth-check.yml` result (automated)
- Check for `status: failed` posts in the repo
- Review GHL Social Planner "Failed" tab

### Monthly

- Verify all social account connections are still active
- Review posting cadence in `brand.yaml` against actual engagement
- Check LinkedIn token expiry (renew proactively at ~50 days if approaching 60-day limit)

### Quarterly

- Rotate `GHL_API_KEY` as a security best practice
- Review and clean up `status: failed` posts (archive or delete files)
- Review post templates and cadence with Dave

---

## 9. Contact and Escalation

| Issue | Contact |
|-------|---------|
| GHL API changes / breakage | Bob (GHL specialist) via Telegram |
| GitHub Actions / infra | Chuck or Tara |
| Content quality / post approval | Dave directly |
| Social account access (OAuth) | Dave (account owner) |
| GHL platform issues | GHL support + [GHL status page](https://status.gohighlevel.com) |

---

*[Bob - claude-sonnet-4-6] — Forge #2 Docs Phase*
