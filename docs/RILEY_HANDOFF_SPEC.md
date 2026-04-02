# Riley Handoff Spec — PR-Driven Content Creation Workflow

**Issue:** [VelocityPoint/social-calendar#2](https://github.com/VelocityPoint/social-calendar/issues/2)
**Audience:** Riley AI agent — content generation workflow specification
**Purpose:** Defines exactly how Riley generates and submits social media posts for GHL publishing

---

## 1. Riley's Role in the Pipeline

Riley is the content-generation agent. Riley's job is to:
1. Generate post copy for each platform
2. Create properly formatted `.md` post files
3. Open a GitHub PR to `VelocityPoint/social-calendar`
4. Respond to Dave's review feedback if needed

Riley does **not** publish posts. Riley does **not** set `status: ready`. Publishing is triggered when Dave merges the PR.

---

## 2. PR-Driven Workflow

```
Riley generates post content
  │
  ├── Creates one .md file per platform
  │   (e.g., 2026-04-15-linkedin-spring.md, 2026-04-15-facebook-spring.md)
  │
  ├── All files have status: draft
  │
  └── Opens PR to VelocityPoint/social-calendar
        Title: "[Riley] <description of batch>"
        Body: table of posts, themes, any notes for Dave

Dave reviews the PR
  │
  ├── Reads post copy in the GitHub diff (Markdown renders cleanly)
  │
  ├── May edit content inline (Riley doesn't need to respond to minor edits)
  │
  ├── If content needs revision: requests changes in PR comments
  │   └── Riley pushes a new commit addressing the feedback
  │
  └── Approves by setting status: ready in each approved post file
        then merges to main

GitHub Actions publishes approved posts via GHL API
```

---

## 3. File Location and Naming

### Directory structure

```
brands/secondring/calendar/YYYY/MM/YYYY-MM-DD-{platform}-{slug}.md
```

**Examples:**
```
brands/secondring/calendar/2026/04/2026-04-15-linkedin-spring-launch.md
brands/secondring/calendar/2026/04/2026-04-15-facebook-spring-launch.md
brands/secondring/calendar/2026/04/2026-04-17-instagram-ai-answering.md
brands/secondring/calendar/2026/04/2026-04-17-gbp-ai-answering.md
```

### Naming rules

- Format: `YYYY-MM-DD-{platform}-{slug}.md`
- `{platform}` must be one of: `linkedin`, `facebook`, `instagram`, `gbp`, `x`
- `{slug}` is short, descriptive, kebab-case (e.g., `never-miss`, `spring-launch`, `ai-receptionist`)
- **One file per platform per post**. Do not combine multiple platforms in one file.
- Create the `YYYY/MM/` directory if it doesn't exist.

---

## 4. Required Frontmatter

Every post file begins with YAML frontmatter between `---` delimiters.

### Minimal valid frontmatter

```yaml
---
id: 2026-04-15-linkedin-spring-launch
publish_at: 2026-04-15T09:00:00-07:00
platforms:
  - linkedin
status: draft
brand: secondring
author: dave
---
```

### Full frontmatter with optional fields

```yaml
---
id: 2026-04-15-linkedin-spring-launch
publish_at: 2026-04-15T09:00:00-07:00
platforms:
  - linkedin
status: draft
brand: secondring
author: dave
tags:
  - spring-2026
  - ai-answering
  - service-business
campaign: spring-2026-launch
---
```

### Field reference

| Field | Required | Who sets it | Valid values | Notes |
|-------|----------|-------------|-------------|-------|
| `id` | ✅ | Riley | `YYYY-MM-DD-{slug}` | Must match filename slug. Pattern: `^\d{4}-\d{2}-\d{2}-.+$` |
| `publish_at` | ✅ | Riley | ISO 8601 + tz | `2026-04-15T09:00:00-07:00` (PDT) or `2026-04-15T16:00:00Z` (UTC) |
| `platforms` | ✅ | Riley | List | `facebook`, `instagram`, `linkedin`, `gbp`, `x` |
| `status` | ✅ | Riley | `draft` | **Always `draft` from Riley.** Dave sets `ready`. |
| `brand` | ✅ | Riley | `secondring` | Must match a `brands/` directory |
| `author` | ✅ | Riley | `dave` or `velocitypoint` | `dave` = Dave's personal accounts |
| `tags` | ❌ | Riley | List of strings | Optional. Used for content filtering and reporting |
| `campaign` | ❌ | Riley | String slug | Optional. Groups related posts (e.g., `spring-2026-launch`) |

### Fields Riley must NEVER set

| Field | Reason |
|-------|--------|
| `status: ready` | Dave sets this during PR review. Setting it bypasses the approval gate. |
| `ghl_post_id` | Written by publisher after successful API call. |
| `published_at` | Written by publisher. |
| `error` | Written by publisher on failure. |
| `account_id` | Normally resolved from `brand.yaml`. Only used for overrides. |

---

## 5. Post Body (Copy)

The post body goes after the closing `---` delimiter. This is what Dave reads in the GitHub PR diff.

### Single-platform body (recommended — one file per platform)

```markdown
---
id: 2026-04-15-facebook-spring-launch
publish_at: 2026-04-15T08:00:00-07:00
platforms:
  - facebook
status: draft
brand: secondring
author: dave
---

Spring is the busiest season for service businesses — and the most likely time
customers call while you're on a job.

Second Ring's AI answering service means you never miss that call. It answers,
handles the conversation, and books the appointment. You keep working.

$297/month. 30-day money-back guarantee.
Book a free demo at second-ring.com

#SecondRing #NeverMissACall #ServiceBusiness
```

### Multi-platform body (alternative — one file, multiple platforms)

If the same post goes to multiple platforms with identical copy:

```markdown
---
id: 2026-04-17-spring-multi-platform
publish_at: 2026-04-17T09:00:00-07:00
platforms:
  - linkedin
  - facebook
status: draft
brand: secondring
author: dave
---

Your copy here (applies to all listed platforms).

Keep in mind: LinkedIn = professional tone, max 3,000 chars.
Facebook = conversational, max 63,000 chars.
```

**Riley's preference:** One file per platform allows Dave to review and approve/reject each platform independently. Prefer separate files.

---

## 6. Schema Validation Rules

The `validate-pr.yml` GitHub Actions workflow runs `validate-post.py` on every PR. Riley's posts must pass these checks:

### Required field checks

| Rule | Error if violated |
|------|------------------|
| `id` present and matches pattern `YYYY-MM-DD-*` | `id is required` or `id does not match pattern` |
| `publish_at` present | `publish_at is required` |
| `publish_at` has timezone offset | `publish_at must include timezone offset` |
| `platforms` is non-empty list | `platforms must have at least 1 item` |
| Each platform in valid enum | `Unknown platform: <value>` |
| `status` present | `status is required` |
| `status` in valid enum | `Invalid status: <value>` |
| `brand` present | `brand is required` |
| `author` present | `author is required` |
| `author` in `dave\|velocitypoint` | `Invalid author: <value>` |

### Character limit checks (body, per platform)

| Platform | Character limit |
|----------|----------------|
| `linkedin` | 3,000 |
| `facebook` | 63,000 |
| `instagram` | 2,200 |
| `gbp` | 1,500 |
| `x` | 280 |

### Account mapping check

If `ghl_mode: true` (the default), `validate-post.py` also checks that `brand.yaml` has an account configured for each `author` + `platform` combination. This check is a **warning**, not a failure, if `brand.yaml` doesn't yet have real account IDs (during bootstrap).

---

## 7. Sample Post Templates by Platform

### LinkedIn — Professional / Thought Leadership

```markdown
---
id: 2026-04-15-linkedin-never-miss
publish_at: 2026-04-15T09:00:00-07:00
platforms:
  - linkedin
status: draft
brand: secondring
author: dave
tags:
  - ai-answering
  - service-business
---

The most expensive call in your business is the one you didn't answer.

That customer called while you were on a job. They didn't leave a voicemail.
They called your competitor instead.

Second Ring's AI answering service picks up every call, 24/7. It sounds human,
handles the conversation intelligently, and books the appointment directly to
your calendar.

We built this because service businesses deserve the same answering quality
as enterprise companies — without the enterprise price tag.

$297/month. No contracts. Try it at second-ring.com

#AI #SmallBusiness #ServiceBusiness #NeverMissACall
```

**LinkedIn tone notes:** Professional, data-informed, thought leadership framing. Less promotional, more insight-driven. Hashtags at the end, 3-5 max.

---

### Facebook — Conversational / Community

```markdown
---
id: 2026-04-15-facebook-spring-busy
publish_at: 2026-04-15T08:00:00-07:00
platforms:
  - facebook
status: draft
brand: secondring
author: dave
tags:
  - spring
  - service-business
---

Spring busy season is here — are you ready?

For HVAC techs, plumbers, landscapers, and home service pros, spring means
the phone rings constantly. That's great news. Unless you're on a job when
it rings.

Second Ring answers every call while you're working. Our AI handles the
conversation, answers questions about your services, and books the appointment.
You get a text with the summary.

No missed calls. No voicemails to return at 8pm. Just a full calendar.

Sound interesting? 30-day money-back guarantee. Try it at second-ring.com

#SecondRing #HomeServices #HVAC #Plumber #Landscaping #SmallBusiness
```

**Facebook tone notes:** Conversational, friendly, relatable. OK to use some exclamation points (sparingly). Address the reader directly ("you"). Include relevant hashtags for discovery.

---

### Instagram — Visual + Short + Punchy

```markdown
---
id: 2026-04-15-instagram-never-miss
publish_at: 2026-04-15T12:00:00-07:00
platforms:
  - instagram
status: draft
brand: secondring
author: dave
tags:
  - ai
  - smallbusiness
---

Every missed call is a missed customer.

Second Ring answers for you — 24/7.

🔗 second-ring.com (link in bio)

#SecondRing #NeverMissACall #AI #SmallBusiness #ServiceBusiness
```

**Instagram tone notes:** Very short. Lead with the hook. Include a CTA and link in bio reference. Heavy on hashtags for discoverability (up to 30). Emojis are appropriate but don't overdo. Under 2,200 chars but aim for under 300 for readability.

---

### Google Business Profile — Local / Service-Focused

```markdown
---
id: 2026-04-15-gbp-spring-service
publish_at: 2026-04-15T09:00:00-07:00
platforms:
  - gbp
status: draft
brand: secondring
author: dave
tags:
  - gbp
  - local
---

Spring home services at full speed? Second Ring answers every call so you
never miss a customer. 24/7 AI answering for service businesses.

$297/month — try it free for 30 days at second-ring.com
```

**GBP tone notes:** Short and local-SEO-friendly. Include the service category and relevant keywords naturally. No hashtags. Max 1,500 chars. Clear CTA. GBP posts are primarily for local search visibility.

---

### Twitter/X — Short / Engaging / Shareable

```markdown
---
id: 2026-04-15-x-never-miss
publish_at: 2026-04-15T10:00:00-07:00
platforms:
  - x
status: draft
brand: secondring
author: dave
tags:
  - x
  - ai
---

Every call you miss costs you a customer.

Second Ring's AI answers 24/7 so you can focus on the work.

$297/mo. second-ring.com
```

**X tone notes:** Under 280 characters (hard limit). Punchy. No hashtags in the character budget unless they're the CTA. Focus on one idea.

---

## 8. Batch Post Generation Guidelines

### Campaign structure

A typical batch PR covers 1-2 weeks of content:

```
PR: "[Riley] April Week 2 — Service Business Theme"

Files:
  2026-04-14-linkedin-spring-rush.md      (Mon 9am)
  2026-04-15-facebook-never-miss.md       (Tue 8am)
  2026-04-16-instagram-ai-demo.md         (Wed 12pm)
  2026-04-17-gbp-spring-service.md        (Thu 9am)
  2026-04-17-linkedin-technician-tip.md   (Thu 2pm)
  2026-04-18-x-friday-quote.md            (Fri 10am)
```

### PR body format

```markdown
## April Week 2 — Service Business Theme

Ref #2

**Theme:** Spring rush + AI answering for service pros

| File | Platform | Scheduled | Theme |
|------|----------|-----------|-------|
| 2026-04-14-linkedin-spring-rush.md | LinkedIn | Apr 14 9am PDT | Spring busy season |
| 2026-04-15-facebook-never-miss.md | Facebook | Apr 15 8am PDT | Missed calls cost customers |
| 2026-04-16-instagram-ai-demo.md | Instagram | Apr 16 12pm PDT | Visual + short |
| 2026-04-17-gbp-spring-service.md | GBP | Apr 17 9am PDT | Local SEO |
| 2026-04-17-linkedin-technician.md | LinkedIn | Apr 17 2pm PDT | Technician vs receptionist |
| 2026-04-18-x-friday-quote.md | X | Apr 18 10am PDT | Friday engagement |

**Notes for Dave:**
- LinkedIn posts lean on the "missed call = missed revenue" angle — high-performing topic based on our content pillars
- Instagram post needs an image from assets/ — I've referenced `assets/ai-phone-banner.jpg`
- GBP post targets spring home services keywords
```

### Recurring content generation

For weekly recurring content, generate 4 weeks at a time in one PR:

```
brands/secondring/calendar/2026/04/2026-04-07-linkedin-tip-week1.md
brands/secondring/calendar/2026/04/2026-04-14-linkedin-tip-week2.md
brands/secondring/calendar/2026/04/2026-04-21-linkedin-tip-week3.md
brands/secondring/calendar/2026/04/2026-04-28-linkedin-tip-week4.md
```

Dave reviews the full batch, merges once, all 4 posts schedule in GHL. This is the preferred approach for recurring content (GHL's native recurring feature is UI-only and not accessible via API).

---

## 9. Review and Approval Process

### Dave's review process

1. Dave reads each post in the PR diff (the Markdown body renders cleanly in GitHub)
2. If content is approved as-is: Dave sets `status: ready` in the frontmatter and merges
3. If content needs changes: Dave requests changes via PR comment
4. Riley pushes a new commit with revisions
5. Process repeats until Dave approves

### Handling PR feedback

If Dave comments with feedback:
- Small edits (typos, word choice): Dave often makes the edit directly
- Larger revisions: Riley should push a new commit with the requested changes
- Rejection of a post: Dave will close the PR or leave the file at `status: draft` and not merge it

### What happens after merge

1. `publish.yml` triggers on push to `main`
2. Publisher processes files with `status: ready`
3. On success: frontmatter updated to `status: scheduled`, `ghl_post_id` added
4. On failure: frontmatter updated to `status: failed`, `error` added
5. Publisher commits these changes with `[skip ci]` to prevent loop

Riley does not need to take any action after a successful merge. If a post fails, Bob or Dave will investigate and re-queue.

---

## 10. Common Mistakes to Avoid

| Mistake | Why it's a problem | Fix |
|---------|---------------------|-----|
| `status: ready` in new file | Bypasses Dave's review | Always use `status: draft` |
| Missing timezone in `publish_at` | CI check fails | Add `-07:00` (PDT) or `-08:00` (PST) or `Z` |
| `platform: linkedin` (singular) | Schema expects `platforms:` (list) | Use `platforms:\n  - linkedin` |
| `author: davelawler-vp` | Not a valid author | Use `dave` or `velocitypoint` |
| Setting `ghl_post_id` | Publisher overwrites it anyway; confuses state | Leave this field out |
| Character limit exceeded | CI check fails | Check limits per platform (see Section 6) |
| Wrong brand name | Publisher can't find brand config | Use `secondring` (lowercase, no spaces) |
| Committing to `main` directly | Content goes live without review | Always work on a branch and open a PR |

---

*[Bob - claude-sonnet-4-6] — Forge #2 Docs Phase*
