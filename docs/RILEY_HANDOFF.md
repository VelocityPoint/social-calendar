# Riley Handoff — Post Generation Guide

This document tells Riley (the content-generation agent) exactly how to create social media post files for the GHL Social Planner pipeline.

---

## Your Job

Generate post `.md` files and open a PR to `VelocityPoint/social-calendar`. Dave reviews the posts in the GitHub PR diff. When Dave approves and merges, the posts are automatically scheduled via the GHL Social Planner API.

You create the files. Dave controls what gets published.

---

## File Location

All post files go here:

```
brands/secondring/calendar/YYYY/MM/YYYY-MM-DD-{platform}-{slug}.md
```

**Examples:**
```
brands/secondring/calendar/2026/04/2026-04-01-linkedin-never-miss.md
brands/secondring/calendar/2026/04/2026-04-01-facebook-never-miss.md
brands/secondring/calendar/2026/04/2026-04-03-linkedin-ai-receptionist.md
```

**Rules:**
- One file per platform. If the same content goes to LinkedIn and Facebook, create two files.
- Use lowercase platform names in the filename: `linkedin`, `facebook`, `instagram`, `google_business`
- Slug should be short, descriptive, and kebab-case (e.g., `never-miss`, `ai-receptionist`, `q2-launch`)
- Create the directory structure (`YYYY/MM/`) if it doesn't exist

---

## Required Frontmatter

Every post file starts with YAML frontmatter between `---` delimiters:

```yaml
---
platform: linkedin
scheduled_at: 2026-04-03T14:00:00-07:00
author: dave
status: draft
---
```

| Field | Required | What to set | Notes |
|-------|----------|-------------|-------|
| `platform` | Yes | One of: `linkedin`, `facebook`, `instagram`, `google_business` | Exactly one platform per file |
| `scheduled_at` | Yes | ISO 8601 datetime with timezone offset | Must be in the future. Use Pacific time (`-07:00` PDT / `-08:00` PST) |
| `author` | Yes | `dave` or `velocitypoint` | `dave` = Dave's personal accounts. `velocitypoint` = company accounts |
| `status` | Yes | Always set to `draft` | Dave changes this to `ready` during PR review |

### Optional Frontmatter

```yaml
tags:
  - ai-answering
  - never-miss-a-call
  - q2-2026
campaign: q2-2026-launch
```

| Field | Required | What to set |
|-------|----------|-------------|
| `tags` | No | Content tags for filtering (list of strings) |
| `campaign` | No | Campaign slug to group related posts |

---

## Post Body

The post body goes after the closing `---`. This is the actual content that gets published to the platform.

```markdown
---
platform: facebook
scheduled_at: 2026-04-09T08:00:00-07:00
author: dave
status: draft
tags:
  - ai-answering
  - small-business
---

How many calls did you miss last month?

For most service businesses, the answer is "more than I know." Calls go unanswered
while you're on a job. Voicemails pile up. Some customers leave a message — most
just call your competitor.

Second Ring's AI answering service picks up every call, handles the conversation,
and books the appointment. You keep working. The calendar fills up.

$297/month. 30-day money-back guarantee. Try it risk-free at second-ring.com
```

---

## Character Limits Per Platform

| Platform | Frontmatter value | Max characters |
|----------|-------------------|----------------|
| LinkedIn | `linkedin` | 3,000 |
| Facebook | `facebook` | 63,000 |
| Instagram | `instagram` | 2,200 |
| Google Business Profile | `google_business` | 1,500 |

The `validate-pr.yml` workflow enforces these limits. If your post exceeds the limit, the PR check will fail with a clear error.

---

## What Happens After Dave Merges

1. Dave reviews your PR, may edit the content, and sets `status: ready` on approved posts
2. Dave merges the PR to `main`
3. GitHub Actions (`publish.yml`) triggers automatically
4. The publisher reads each `.md` file with `status: ready`
5. For each post: resolves `author` → GHL account ID → calls GHL API with `scheduledAt`
6. GHL holds the post and publishes it at the `scheduled_at` time
7. Publisher updates the file: `status: scheduled`, adds `ghl_post_id` and `published_at`
8. Publisher commits these status updates with `[skip ci]`

You do not need to do anything after opening the PR. The pipeline handles the rest.

---

## Example Post File

Copy this template and fill in the content:

```markdown
---
platform: linkedin
scheduled_at: 2026-04-15T09:00:00-07:00
author: dave
status: draft
tags:
  - ai-answering
  - service-business
---

Your post content goes here. Write for the specific platform.

Include hashtags at the end if appropriate for the platform.

#SecondRing #NeverMissACall
```

---

## What NOT to Do

- **Don't set `ghl_post_id`** — this is written by the publisher after successful scheduling
- **Don't set `status: ready`** — Dave does that during PR review. Always use `status: draft`
- **Don't set `published_at`** — this is written by the publisher
- **Don't set `error`** — this is written by the publisher on failure
- **Don't put PII in file names** — no customer names, emails, or phone numbers in the path
- **Don't use `platforms:` (plural)** — GHL mode uses `platform:` (singular), one file per platform
- **Don't omit the timezone offset** — `2026-04-01T09:00:00` without `-07:00` or `Z` will fail validation

---

## Batch Posts (Cross-Platform Campaigns)

To post the same campaign across multiple platforms, create one file per platform in a single PR:

```
brands/secondring/calendar/2026/04/2026-04-15-linkedin-spring-launch.md
brands/secondring/calendar/2026/04/2026-04-15-facebook-spring-launch.md
brands/secondring/calendar/2026/04/2026-04-15-instagram-spring-launch.md
brands/secondring/calendar/2026/04/2026-04-15-google_business-spring-launch.md
```

Each file has its own `platform:` value and content tailored to that platform's format and character limits. Dave reviews and approves the batch in one PR.

---

## Recurring Content

GHL's native recurring post feature is UI-only. To schedule recurring content, generate a batch of future-dated posts. For example, 4 weeks of LinkedIn posts:

```
2026-04-07-linkedin-week1-tip.md   (scheduled_at: 2026-04-07T09:00:00-07:00)
2026-04-14-linkedin-week2-tip.md   (scheduled_at: 2026-04-14T09:00:00-07:00)
2026-04-21-linkedin-week3-tip.md   (scheduled_at: 2026-04-21T09:00:00-07:00)
2026-04-28-linkedin-week4-tip.md   (scheduled_at: 2026-04-28T09:00:00-07:00)
```

Dave reviews the full batch, merges once, and all 4 posts get scheduled.

---

[Scribe - Technical Writer - claude-opus-4-6]
