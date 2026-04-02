# Social Calendar Workflow — Formalized Process

**Repo:** VelocityPoint/social-calendar
**Owner:** Bob (automation), Dave (approvals)
**Purpose:** The canonical, repeatable workflow for social content from idea to live post
**Audience:** Any agent or human working with the social calendar — now and in future resale deployments

---

## 1. The Two Gates

Every post must pass two explicit approval gates before it can go live. Neither gate can be skipped.

```
Gate 1: GitHub PR Review
  → Dave approves the COPY (what we're saying, to whom, when)
  → Enforced by: PR merge requirement + validate-pr.yml CI

Gate 2: GHL Social Planner Review
  → Dave activates the POST in GHL (visual preview, final confirmation)
  → Enforced by: publisher creates post in GHL as DRAFT; auto-fire disabled
```

No post fires automatically. Every post requires a human to touch it twice.

---

## 2. Full Pipeline (All Stages)

```
[Stage 1: Content Creation]
  Riley (or Bob) generates post content
  Creates .md files in brands/<brand>/calendar/YYYY/MM/
  status: draft
  Opens PR to VelocityPoint/social-calendar

          ↓

[Stage 2: GitHub PR Review — GATE 1]
  Dave reads post copy in the GitHub diff
  Optionally edits content or requests changes
  When satisfied: sets status: ready in each approved file
  Merges the PR to main

          ↓

[Stage 3: Publisher → GHL Draft]
  publish.yml triggers on push to main
  publisher.py detects files with status: ready
  Creates post in GHL Social Planner as DRAFT (not auto-scheduled)
  Writes back status: ghl-pending + ghl_post_id to the .md file
  Notifies Dave via Telegram: "X posts are pending your approval in GHL"

          ↓

[Stage 4: GHL Review — GATE 2]
  Dave opens GHL Social Planner → Social tab → Drafts/Pending queue
  Reviews visual preview of each post (rendered copy, image, platform)
  Confirms scheduling time is correct
  Clicks "Approve" / "Schedule" in GHL for each post
  GHL status → Scheduled

          ↓

[Stage 5: Live — GHL Fires the Post]
  GHL publishes post at the scheduled time natively
  publisher.py detects success (via polling or webhook)
  Writes back status: published + published_at to .md file
  Post is live on the target platform(s)
```

---

## 3. Status Lifecycle (Updated)

```
draft
  └─[Dave sets ready in PR]─▶ ready
        └─[merge + publisher creates in GHL as draft]─▶ ghl-pending
              └─[Dave approves in GHL]─▶ scheduled
                    └─[GHL fires at publish_at]─▶ published
                    └─[all retries fail]─▶ failed
```

| Status | Set by | Meaning | Dave action required? |
|--------|--------|---------|----------------------|
| `draft` | Riley / Bob | Work in progress | No |
| `ready` | Dave (in PR) | Copy approved, ready to submit | Merge the PR |
| `ghl-pending` | Publisher | Post in GHL draft queue | ✅ Yes — approve in GHL |
| `scheduled` | GHL / Publisher | GHL has confirmed scheduling | No |
| `published` | GHL / Publisher | Live on platform | No |
| `failed` | Publisher | Something broke | Review error, re-queue |

---

## 4. What Each Role Does

### Riley (Content Agent)
- Generates post copy for each platform
- Creates properly formatted .md files (status: draft, always)
- Opens PR with a table of posts, theme, and notes for Dave
- Responds to Dave's PR feedback with revised commits
- Never sets `status: ready` — that's Dave's gate

### Bob (GHL Automation)
- Maintains the publisher code and GHL adapter
- Monitors pipeline health (failed posts, auth errors)
- Investigates any `status: failed` posts and re-queues
- Builds Telegram notifications for pending approval alerts
- Owns `brand.yaml` updates when accounts change

### Dave (Approver)
- Reviews copy in GitHub PR diff (Gate 1) — sets `status: ready`, merges
- Reviews posts in GHL Social Planner UI (Gate 2) — clicks Approve/Schedule
- Final say on all content before it goes live

---

## 5. File Conventions

### Naming
```
brands/<brand>/calendar/YYYY/MM/YYYY-MM-DD-{platform}-{slug}.md
```

Examples:
```
brands/secondring/calendar/2026/04/2026-04-14-linkedin-spring-rush.md
brands/secondring/calendar/2026/04/2026-04-15-facebook-never-miss.md
```

**One file per platform.** If the same post goes to 3 platforms, create 3 files. This lets Dave approve/reject per platform independently.

### Required Frontmatter

```yaml
---
id: 2026-04-14-linkedin-spring-rush
publish_at: 2026-04-14T09:00:00-07:00
platforms:
  - linkedin
status: draft
brand: secondring
author: dave
tags:
  - spring-2026
  - service-business
---
```

### Publisher-Managed Fields (never set manually)

| Field | Written by | When |
|-------|-----------|------|
| `ghl_post_id` | Publisher | After successful draft creation in GHL |
| `published_at` | Publisher | After GHL confirms live |
| `error` | Publisher | On failure |

---

## 6. PR Format (Standard)

Every PR opening a batch of posts must follow this format:

**Title:** `[Riley] <Theme> — <Date Range>`

**Body:**
```markdown
## <Theme Name>

Ref #<issue-number-if-any>

**Theme:** <one-sentence description of the content angle>
**Brand:** secondring
**Date range:** Apr 14–18, 2026

| File | Platform | Scheduled | Topic |
|------|----------|-----------|-------|
| 2026-04-14-linkedin-spring-rush.md | LinkedIn | Apr 14 9am PDT | Spring busy season |
| 2026-04-15-facebook-never-miss.md | Facebook | Apr 15 8am PDT | Missed calls = lost revenue |
| 2026-04-16-instagram-ai-demo.md | Instagram | Apr 16 12pm PDT | Short punchy visual |

**Notes for Dave:**
- <anything Dave needs to know about the content choices>
- <flag any posts that need an image from assets/>
- <flag any platform-specific considerations>
```

---

## 7. Review Checklist

### Gate 1 — GitHub PR Review (Dave)
- [ ] Copy reads naturally for each platform's audience
- [ ] No factual errors (pricing, features, claims)
- [ ] CTAs are correct (second-ring.com, link in bio, etc.)
- [ ] Scheduling times make sense (not midnight, not a holiday)
- [ ] Images referenced in `creative:` actually exist in `brands/<brand>/assets/`
- [ ] Character limits look fine (CI will catch overruns, but a quick read helps)
- [ ] Set `status: ready` on each approved file
- [ ] Merge the PR

### Gate 2 — GHL Social Planner Review (Dave)
- [ ] Post preview looks correct in GHL UI
- [ ] Correct platform account selected (Dave's personal vs VelocityPoint)
- [ ] Image thumbnail shows correctly (if image post)
- [ ] Scheduling date/time is right
- [ ] Click Approve / Schedule for each post

---

## 8. Cadence & Volume

### Second Ring — Target Cadence

| Platform | Posts/week | Best times (PDT) |
|----------|-----------|-----------------|
| LinkedIn | 3 | Mon 9am, Wed 9am, Fri 9am |
| Facebook | 5 | Mon-Fri 8am or 12pm |
| Instagram | 3 | Tue/Thu 12pm, Sat 10am |
| X | 7 | Daily 8-10am |
| GBP | 2 | Mon, Thu 9am |

### Batch size
- Riley generates **1–2 weeks** of content per PR
- Review and approve in one sitting
- Merge once → all posts queue in GHL → Dave does Gate 2 review in one GHL session

---

## 9. Resale Product Notes

This pipeline is designed to be resaleable. When deploying for a client:

1. **Add a brand:** Create `brands/<client-slug>/brand.yaml` (see secondring template). No code changes.
2. **Connect GHL accounts:** Client connects their social accounts to their GHL sub-account. Bob gets the account IDs via `ghl_social_list_accounts.py`.
3. **Configure cadence:** Set `cadence:` in `brand.yaml` for their platform preferences.
4. **Set voice and pillars:** `voice:` and `pillars:` in `brand.yaml` drive Riley's content generation.
5. **Train Riley:** Riley's content agent reads `brand.yaml` + any brief files in `brands/<client-slug>/`.

Client-facing positioning:
- "We write the posts, you approve them twice — once in GitHub (if you're technical) or we handle that gate for you, once in your GHL calendar"
- "Posts never go live without your OK"
- "Everything is versioned — you can see every post we've ever made and roll back anything"

---

## 10. Open Technical Work

The following items need to be built before Gate 2 is fully operational:

### 10.1 GHL Draft Mode (REQUIRED)
**Current behavior:** Publisher creates posts in GHL as `scheduled` (auto-fires).
**Required behavior:** Publisher creates posts as GHL drafts or in a "pending approval" state.
**Work:** Investigate GHL API `createPost` for a draft/pending parameter. If not available, create post with `scheduledAt` far in the future as a hold mechanism, or use GHL's built-in review workflow feature.
**Issue:** See social-calendar#<TBD>

### 10.2 Telegram Notification — Pending Approval Alert (REQUIRED)
**Current behavior:** No notification after publisher runs.
**Required behavior:** After publisher creates GHL drafts, send Dave a Telegram message: "X posts are pending your approval in GHL Social Planner."
**Work:** Add Telegram notify step to `publish.yml` after publisher completes.
**Issue:** See social-calendar#<TBD>

### 10.3 Status Polling / Webhook for Published Confirmation (NICE-TO-HAVE)
**Current behavior:** Publisher doesn't know when GHL actually fires the post.
**Required behavior:** After `status: scheduled`, publisher (or a separate cron) detects when GHL confirms the post is live and writes back `status: published`.
**Work:** Either poll GHL `getPost` endpoint or configure GHL webhook for post-published event.
**Issue:** See social-calendar#<TBD>

---

*Formalized by Bob — 2026-04-02*
*This document is the single source of truth for the social calendar workflow.*
*All agents working on this pipeline should read this first.*
