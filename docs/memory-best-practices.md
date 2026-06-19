# Guiding Your Agent's Memory

A practical guide to wiring memory stores into Claude Managed Agents so they get measurably better at a task over time — with a full audit trail.

## Why memory matters

Out of the box, every session starts from zero. Memory stores give an agent durable experience: lessons it wrote in past sessions are read at the start of the next one, so it stops repeating the same mistakes. Paired with an outcome rubric (the examiner) and dreams (periodic consolidation), you get a self-improvement loop where **iterations-to-pass trends toward zero** and every learned fact has a paper trail.

For a regulated workload this is the key property: the agent never grades its own homework, you set the rubric, the verdict is logged, and every memory write is an immutable, attributable, redactable version. Learning is reviewable and revocable.

## The memory store model

- A memory store is a small filesystem mounted at `/mnt/memory/<store>/`. The agent reads and writes it with ordinary file tools.
- Stores attach **at session-create only**, via the `resources[]` array on `POST /v1/sessions`. They **cannot** be set on the agent config — the API rejects it. Your session-orchestration code owns the agent → store mapping.
- Limits: ≤8 stores per session, ≤100 kB per file, version history retained 30 days.
- `access` is `read_write` (default) or `read_only`. Use `read_only` for any store shared across agents or fed by untrusted input — it's the prompt-injection guard.
- **Memory is entirely prompt-driven.** There is no harness that auto-detects what's worth remembering. The per-attachment `instructions` field (≤4,096 chars) on the `resources[]` entry is the *only* thing telling the agent that memory exists and how to use it.

**Recommended architecture: one `read_write` learnings store per workflow.** That's the isolation boundary. Optionally add one frozen `read_only` standards store as a governance contrast ("the manual" vs "what the agent learned"). Don't pre-build empty org-wide or line-of-business layers — add a shared layer only when a *second* workflow would actually reuse it.

## What to put in your agent's `instructions`

Put memory hygiene in the **`instructions` field on the resource attachment**, not in the agent's system prompt. This keeps the system prompt clean and scopes the guidance to sessions where a store is actually attached.

Three things the instructions must do:

1. **Mandate the read.** Agents reliably skip memory when making fast decisions. Be explicit: *"BEFORE you do anything else, list and read every file in `lessons/`."* Reading is a hard requirement; writing stays the agent's judgment call.
2. **Frame the write as reflection for a future agent.** Ask *"what would a FUTURE agent doing this same task want to know?"* — not "what did you learn" (which produces nothing useful from a coordinator's vantage point).
3. **Pre-define the structure.** Tell it the directory (`lessons/`), the format, and a size cap (≤1 KB per file). Don't let it freelance. Lessons must be **transferable rules**, not session notes — "Always check SIU indicators against the 2+ rule" is a lesson; "CLM-2026-0431 had a daycare" is not.

## The converge-don't-accumulate rule

Left unprompted, agents create one micro-file per session and the store balloons into dozens of near-duplicates. The fix lives in the write instruction: the agent **already read `lessons/` at the start**, so it *knows* what's covered. The test for every insight is:

> Already covered by a file I read? → write nothing.
> Adds nuance to an existing topic? → **EDIT that file**, fold it in.
> Genuinely new topic? → only then create a new file.
> Aim for under ~10 topic files total.

Concurrent sessions editing the same topic file race (last-write-wins), but lost lessons get re-learned by future sessions — it self-heals. Dreams are the periodic *editor* (dedupe, restructure, drop PII into a **new** store you diff and approve), not the convergence mechanism. A separate "librarian" agent isn't needed; session agents converge inline.

## Example prompt text

Attach on every `POST /v1/sessions` `resources[]` entry:

```python
MEM_READ = ("Before starting your task, list this directory with glob and read what's "
            "relevant. Past lessons here help you avoid repeating mistakes — apply them.")

MEM_WRITE = ("Before going idle, reflect: what would a FUTURE agent doing this same task want to know? "
  "You already read lessons/ at the start — so you KNOW what's already written down. "
  "The test for every insight is: IS THIS ALREADY COVERED BY A FILE I READ? If yes, write nothing. "
  "If it adds a nuance to an existing topic, EDIT that file and fold it in where it belongs. "
  "Only create a new file when the insight genuinely fits no existing topic — lessons/ should converge "
  "to a SMALL, stable set of topic files (aim for under ~10 total), not grow by one file per session. "
  "HIGHEST PRIORITY — grader feedback: if an outcome grader returned needs_revision, you MUST record "
  "what it caught in lessons/grader-<rubric-section-slug>.md. READ it first, MERGE the new rule in, "
  "do NOT create a near-duplicate filename. "
  "Your own discoveries follow the same rule: ≤1 KB per addition; GENERAL rules, not session notes.")

resources = [{
    "type": "memory_store",
    "memory_store_id": STORE_ID,
    "access": "read_write",
    "instructions": f"Your accumulated {workflow} lessons. {MEM_READ} {MEM_WRITE}",
}]
```

Dream consolidation (`POST /v1/dreams`, run on your own cron):

```
Identify the rubric criteria the outcome grader most often returned as gaps, the root cause,
and the fix. Promote any pattern observed in 3+ sessions to a standing rule under /lessons/.
Resolve contradictions by recency. Merge duplicate lessons. Drop one-off data quirks,
session-specific notes (claim numbers, dates), and PII. Keep entries general and transferable.
Each file ≤1KB.
```

## Common mistakes

- **One-file-per-session sprawl.** Ten micro-files that are really two topics. Fix: the converge instruction above.
- **Session notes instead of rules.** Claim numbers, dates, PII. Fix: "general and transferable" in the instruction; dreams strip the rest.
- **Hygiene in the system prompt instead of `instructions`.** Bloats the prompt and fires even when no store is attached.
- **Typo `readonly` instead of `read_only`.** Silently escalates to `read_write` — a privilege-escalation bug. Double-check the literal.
- **`read_write` store on sessions processing untrusted input.** Claimant emails or fetched web content can poison the well — written now, trusted later. Use `read_only` for shared stores; only the workflow's own scratch store is writable.
- **Hardcoded mount paths baked into lesson content.** Store slugs change; keep paths out of the lesson body.
- **Expecting grader feedback to auto-persist.** It doesn't. The agent must be *instructed* to log what the grader caught.
- **Pre-building empty org/LOB layers.** Start with one store per workflow; add shared layers only when there's content to fill them.
- **Assuming dreams prune.** They produce a new store; the input keeps growing. Plan retention yourself.
