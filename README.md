# Claude Managed Agents — Workshop Kit

Starter configs and a deploy script for building **Claude Managed Agents (CMA)** — Anthropic-hosted agents that run in cloud sandboxes, call your tools over MCP, and coordinate sub-agents.

Eight insurance-shaped examples across three pillars — **claims**, **service**, **sales** — packaged as **two independent one-day workshops**: a Claims track and a Service & Sales track. Each example is a near-literal `POST /v1/agents` body plus a one-screen deploy script. What you read is what hits the wire.

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

# 1. Pick a pillar (claims | service | sales), then an example
$EDITOR examples/claims/fnol-triage.yaml

# 2. Deploy it — creates the agent, prints agt_... and a Console URL
python deploy.py examples/claims/fnol-triage.yaml

# 3. Run it — creates a session, opens the SSE stream, sends your prompt, prints events
python run.py --agent agt_... "Triage claim CLM-2026-0001"

# 4. Work through your track in lab order (tables below). Copy any example as your own starting point.
```

`deploy.py` defines the agent (one-time, versioned). `run.py` is the minimal **client** every CMA integration needs — the part *you* still own: trigger a session, stream events, handle `requires_action`. In production this becomes a webhook handler, a cron, a button in your UI; here it's 100 lines you can read top to bottom.

## Directory map

```
workshop-kit/
├── README.md / CLAUDE.md              # this file / Claude Code context
├── deploy.py                          # define: YAML/JSON → POST /v1/agents. --dry-run to preview.
├── run.py                             # invoke: session create → SSE stream → send prompt → print events
├── examples/
│   ├── claims/
│   │   ├── fnol-triage.yaml           # first agent — single agent, one MCP
│   │   ├── siu-referral.yaml          # + memory store (learns fraud patterns)
│   │   └── adjudication.yaml          # multi-agent — 3-tier reader/analyst/writer
│   ├── service/
│   │   ├── coverage-explainer.yaml    # first agent + memory store
│   │   ├── add-vehicle.yaml           # human-in-loop write (requires_action pattern)
│   │   └── household-review.yaml      # multi-agent — 3-tier readers/writer
│   └── sales/
│       ├── quote-builder.yaml         # multi-MCP (rating + CRM + product catalog)
│       └── renewal-retention.yaml     # + outcomes rubric (self-grading)
├── MCP-SERVERS.md                     # workshop mock URLs + how to swap in your own
└── docs/
    └── memory-best-practices.md       # the memory `instructions` pattern
```

The examples ship pointing at **hosted mock MCP servers** (synthetic data) so they run out of the box. See [`MCP-SERVERS.md`](MCP-SERVERS.md) to swap in your own — it's a one-line `url:` edit per server.

## YAML or JSON?

**Either.** The CMA API speaks JSON; YAML is just an authoring convenience (comments, multiline `system:` prompts, multi-doc fleets). `deploy.py` accepts both — `yaml.safe_load` parses JSON since JSON ⊂ YAML.

`examples/claims/fnol-triage.{yaml,json}` are the same agent in both syntaxes. To get JSON for any YAML example, `python deploy.py --dry-run <file.yaml>` prints the exact JSON that hits the wire.

## Workshop tracks

### Claims track

| Lab | Example | Teaches |
|---|---|---|
| 1 | `claims/fnol-triage` | first agent — config, one MCP, the gotchas |
| 2 | `claims/siu-referral` | **memory** (learns fraud patterns) + **human-in-loop** (`refer_to_siu` parks at `requires_action`) |
| 3 | `claims/adjudication` + `adjudication-rubric.md` | **multi-agent** 3-tier + **outcomes** (rubric-graded decision memo) |

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
