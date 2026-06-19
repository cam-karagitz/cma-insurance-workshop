# Claude Managed Agents — Workshop Kit

Starter configs and a deploy script for building **Claude Managed Agents (CMA)** — Anthropic-hosted agents that run in cloud sandboxes, call your tools over MCP, and coordinate sub-agents.

Six insurance-shaped examples across three pillars — **claims**, **service**, **sales** — each a near-literal `POST /v1/agents` body plus a one-screen deploy script. What you read is what hits the wire.

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

# 2. Fill in the placeholders (MCP URLs, metadata.owner)

# 3. Deploy it
python deploy.py examples/claims/fnol-triage.yaml

# 4. Work across pillars in complexity order (table below). Copy any example as your own starting point.
```

## Directory map

```
workshop-kit/
├── README.md / CLAUDE.md              # this file / Claude Code context
├── deploy.py                          # YAML → POST /v1/agents (+ environment). Stdlib + requests + pyyaml.
├── examples/
│   ├── claims/
│   │   ├── fnol-triage.yaml           # simplest — single agent, one MCP
│   │   └── adjudication.yaml          # capstone — full 3-tier multi-agent
│   ├── service/
│   │   ├── coverage-explainer.yaml    # + memory store
│   │   └── add-vehicle.yaml           # human-in-loop write (requires_action pattern)
│   └── sales/
│       ├── quote-builder.yaml         # multi-MCP (rating + CRM + product catalog)
│       └── renewal-retention.yaml     # + outcomes rubric (self-grading)
├── MCP-SERVERS.md                     # workshop mock URLs + how to swap in your own
└── docs/
    └── memory-best-practices.md       # the memory `instructions` pattern
```

The examples ship pointing at **hosted mock MCP servers** (synthetic data) so they run out of the box. See [`MCP-SERVERS.md`](MCP-SERVERS.md) to swap in your own — it's a one-line `url:` edit per server.

## Suggested learning order

The examples are sequenced by **complexity, not pillar** — cross pillars to layer one new concept at a time:

| # | Example | Adds |
|---|---|---|
| 1 | `claims/fnol-triage` | single agent, one MCP, deny-by-default toolset |
| 2 | `service/coverage-explainer` | memory store attached at session-create |
| 3 | `service/add-vehicle` | human-in-the-loop write — `always_ask` → `requires_action` |
| 4 | `sales/quote-builder` | multiple MCP servers, per-tool blocklists |
| 5 | `sales/renewal-retention` | outcomes rubric — agent self-grades against criteria |
| 6 | `claims/adjudication` | 3-tier multi-agent (orchestrator / readers / writer) |

## Docs

- Managed Agents overview — https://platform.claude.com/docs/en/managed-agents/overview
- Quickstart — https://platform.claude.com/docs/en/managed-agents/quickstart
- API reference — https://platform.claude.com/docs/en/api/managed-agents
