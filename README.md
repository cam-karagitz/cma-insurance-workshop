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

# 2. Deploy it — creates the agent, prints agt_... and a Console URL
python deploy.py examples/claims/fnol-triage.yaml

# 3. Run it — creates a session, opens the SSE stream, sends your prompt, prints events
python run.py --agent agt_... "Triage claim CLM-2026-0001"

# 4. Work across pillars in complexity order (table below). Copy any example as your own starting point.
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

## YAML or JSON?

**Either.** The CMA API speaks JSON; YAML is just an authoring convenience (comments, multiline `system:` prompts, multi-doc fleets). `deploy.py` accepts both — `yaml.safe_load` parses JSON since JSON ⊂ YAML.

`examples/claims/fnol-triage.yaml` and `examples/claims/fnol-triage.json` are the **same agent in both syntaxes**. Prove it:

```bash
diff <(python deploy.py --dry-run examples/claims/fnol-triage.yaml) \
     <(python deploy.py --dry-run examples/claims/fnol-triage.json)
# (no output = identical request bodies)
```

To get JSON for any YAML example: `python deploy.py --dry-run <file.yaml>` prints the exact JSON that hits the wire — copy it into a `.json` file or straight into curl / your SDK of choice.

## Suggested learning order

Two tracks depending on your format:

**Single session** — sequence by complexity, one new concept per lab:
`claims/fnol-triage` → `service/coverage-explainer` → `service/add-vehicle` → `sales/quote-builder` → `sales/renewal-retention` → `claims/adjudication`

**Two-day, domain-per-day** — Day 1 builds the architecture, Day 2 adds the production features:

| Day | Theme | Labs | Concepts |
|---|---|---|---|
| **1** | Build & orchestrate | `claims/fnol-triage` → `claims/adjudication` | agent config shape · 3-tier multi-agent · least-privilege tool grants |
| **2** | Make it production-grade | `service/coverage-explainer` → `service/add-vehicle` → `sales/quote-builder` → `sales/renewal-retention` | memory · human-in-loop writes · multi-MCP · outcomes/self-grading |

## Docs

- Managed Agents overview — https://platform.claude.com/docs/en/managed-agents/overview
- Quickstart — https://platform.claude.com/docs/en/managed-agents/quickstart
- API reference — https://platform.claude.com/docs/en/api/managed-agents
