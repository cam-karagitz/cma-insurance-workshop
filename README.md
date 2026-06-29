# Claude Managed Agents — Workshop Kit

Starter configs and a deploy script for building **Claude Managed Agents (CMA)** — Anthropic-hosted agents that run in cloud sandboxes, call your tools over MCP, and coordinate sub-agents.

Ten insurance-shaped examples across three pillars — **claims**, **service**, **sales** — packaged as **two independent one-day workshops**: a Claims track and a Service & Sales track. Each example is a near-literal `POST /v1/agents` body plus a one-screen deploy script. What you read is what hits the wire.

## Prerequisites

- An **Anthropic API key** with the `managed-agents-2026-04-01` beta enabled, exported as `ANTHROPIC_API_KEY`
- Your own **Console org** at platform.claude.com (agents are created org-wide)
- **Claude Code** installed (`npm i -g @anthropic-ai/claude-code`) — optional but recommended; this kit ships a `CLAUDE.md` that makes your CC session CMA-aware
- Python 3.10+ for the deploy script

## Quick start

```bash
# 0. (Recommended) In Claude Code, run the onboarding interview — gets a hello-world
#    agent streaming in your language and teaches the 4-resource model:
#    /claude-api managed-agents-onboard

# 0.5 Preflight (~5 seconds). Every MCP tool the examples grant is checked
#     against the LIVE mock servers. A green PREFLIGHT CLEAN means the labs
#     will actually run; do this before anyone deploys anything.
python3 validate.py

# 1. Pick a pillar (claims | service | sales), then an example
$EDITOR examples/claims/fnol-triage.yaml

# 2. Deploy it — creates the agent, prints agt_... and a Console URL
python deploy.py examples/claims/fnol-triage.yaml

# 3. Run it — creates a session, opens the SSE stream, sends your prompt, prints events
python run.py --agent agt_... "Triage claim CLM-2026-0001"
#    Add --ui for a localhost browser view of the SAME run: a live transcript,
#    and an Approve / Deny card when the agent parks at requires_action. Built
#    for the non-engineers in the room. The API key never leaves the python
#    process and nothing is deployed.

# 4. Work through your track in lab order (tables below). Copy any example as your own starting point.

# 5. Build YOUR OWN. Open this repo in Claude Code and type:
#       /new-agent
#    It interviews you (what should it do, which systems, which tools, does an
#    action need a human's approval, who owns the quality bar), then writes a
#    fully-commented example YAML you keep, validates every granted tool
#    against the LIVE mock servers, and deploys + runs it — using the exact
#    same deploy.py / validate.py / run.py you just used by hand. The YAML is
#    the deliverable; the skill never hides it from you.
#
#    TAKE IT WITH YOU — /new-agent is fully self-contained (it carries its own
#    copies of deploy.py, validate.py, run.py and the live tool inventory), so
#    it works in YOUR repos too, not just this one:
#       cp -R .claude/skills/new-agent ~/.claude/skills/        # every Claude Code session
#    Cowork / Claude Desktop: zip it and upload via Customize → Skills:
#       (cd .claude/skills && zip -r ~/new-agent.zip new-agent)
```

## About `deploy.py` and `run.py`

**These are reference implementations, not Anthropic products.** They're ~100 lines each, stdlib + `requests`, no SDK — written so you can see exactly what hits the wire. They're yours: fork them, put them in your CI, wrap them in Terraform, or throw them away and use an official path instead.

| Official alternatives | When you'd use it |
|---|---|
| `ant beta:agents create < agent.yaml` — the Anthropic CLI | interactive use, one-off deploys |
| Anthropic SDKs (`client.beta.agents.create(...)`) — Python, TS, C#, Go, Java, PHP, Ruby | when deploy is part of a larger app |
| `/claude-api managed-agents-onboard` in Claude Code | scaffolds the SDK code + run loop in your language |

**Why these scripts exist anyway:** `deploy.py` handles the multi-doc YAML → subagents-first → roster-auto-wire pattern (the multi-agent capstone) that the CLI and SDKs don't do for you, and `--dry-run` prints the exact JSON body — useful for learning the API shape and for diffing what you wrote against what gets sent. `run.py` is the minimal session client every CMA integration needs — the part *you* still own: trigger a session, stream events, **handle `requires_action`**. It does that for real: when an `always_ask` tool parks the session (a `session.status_idle` whose `stop_reason` is `requires_action`), run.py shows the full pending call and waits for your y/n (or for the Approve button in the `--ui` browser view), posts the `user.tool_confirmation`, and keeps streaming — the agent resumes on the same stream. In production that becomes a webhook handler, a cron, or a button in your adjuster UI; this is the reference for what that button does.

**What they deliberately don't do:** staging vs prod, GitOps, diff-before-promote, rollback. Agents are versioned resources — that's the primitive. Your release process is yours to build on top. The API is the contract; these scripts are one way to call it.

## Directory map

```
workshop-kit/
├── README.md / CLAUDE.md              # this file / Claude Code context
├── deploy.py                          # define: YAML/JSON → POST /v1/agents. --dry-run to preview.
├── run.py  (+ ui.html)                # invoke: session → SSE → events → handle requires_action (terminal or --ui)
├── validate.py                        # PREFLIGHT: every granted MCP tool must exist on its LIVE server
├── examples/
│   ├── claims/
│   │   ├── fnol-triage.yaml           # first agent — single agent, one MCP, the gotchas
│   │   ├── coverage-determination.yaml   (+ rubric)  # 3 MCPs incl. the documents server: a
│   │   │                              #   determination that QUOTES the actual policy form
│   │   ├── next-best-action.yaml         (+ rubric)  # read-only "claims manual" memory store,
│   │   │                              #   one always_ask-gated action, a supervisor-owned rubric
│   │   ├── siu-referral.yaml          # memory store (learns fraud patterns) + human-in-loop
│   │   └── adjudication.yaml             (+ rubric)  # multi-agent 3-tier, 3 MCP servers
│   ├── service/
│   │   ├── coverage-explainer.yaml    # first agent + memory store
│   │   ├── add-vehicle.yaml           # human-in-loop write (requires_action pattern)
│   │   └── household-review.yaml      # multi-agent — 3-tier readers/writer
│   └── sales/
│       ├── quote-builder.yaml         # multiple MCP servers, per-server read allowlists
│       └── renewal-retention.yaml        (+ rubric)  # outcomes rubric (self-grading)
├── MCP-SERVERS.md                     # the live mock servers + the deny-by-default convention
└── docs/
    └── memory-best-practices.md       # the memory `instructions` pattern; read_only vs read_write
```

The examples ship pointing at **hosted mock MCP servers** (synthetic data) so they run out of the box. See [`MCP-SERVERS.md`](MCP-SERVERS.md) to swap in your own — it's a one-line `url:` edit per server.

## YAML or JSON?

**Either.** The CMA API speaks JSON; YAML is just an authoring convenience (comments, multiline `system:` prompts, multi-doc fleets). `deploy.py` accepts both — `yaml.safe_load` parses JSON since JSON ⊂ YAML.

`examples/claims/fnol-triage.{yaml,json}` are the same agent in both syntaxes. To get JSON for any YAML example, `python deploy.py --dry-run <file.yaml>` prints the exact JSON that hits the wire.

## Workshop tracks

### Claims track

| Lab | Example | Teaches |
|---|---|---|
| 1 | `claims/fnol-triage` | first agent — config, one MCP, deny-by-default, the gotchas |
| 2 | `claims/coverage-determination` + its rubric | **three MCP servers** (incl. the `policy-admin` index → `documents` content hop) and a coverage determination grounded in the **actual policy form** — every conclusion must quote the provision it relies on. **Outcomes** rubric owned by coverage counsel |
| 3 | `claims/next-best-action` + its rubric | **memory** ("trained on the claims manual" = a `read_only` store) + **human-in-loop** (the one action it can take is gated `always_ask`) + **outcomes** (a rubric the claims supervisor owns) — all three production features in one example |
| stretch | `claims/adjudication` + its rubric · `claims/siu-referral` | **multi-agent** 3-tier across 3 MCP servers — FNOL through coverage **and liability**, end to end · the deeper memory + human-in-loop combination |

### Service & Sales track

| Lab | Example | Teaches |
|---|---|---|
| 1 | `service/coverage-explainer` | first agent + memory store |
| 2 | `service/add-vehicle` | human-in-loop write (`requires_action`) |
| 3 | `sales/quote-builder` | multiple MCP servers |
| 4 | `sales/renewal-retention` | outcomes rubric (self-grading) |
| 5 | `service/household-review` | multi-agent — 3-tier readers/writer |

Each track is self-contained. Run whichever matches your domain; both teach the same CMA concepts. Attendees leave each day with working pilot agents in that domain — no cross-day dependency.

## Docs

- Managed Agents overview — https://platform.claude.com/docs/en/managed-agents/overview
- Quickstart — https://platform.claude.com/docs/en/managed-agents/quickstart
- API reference — https://platform.claude.com/docs/en/api/managed-agents
