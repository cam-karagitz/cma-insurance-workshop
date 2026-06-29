# Claude Managed Agents — Workshop Kit

You are helping build **Claude Managed Agents (CMA)**: Anthropic-hosted agents that run in cloud sandboxes. All calls require header `anthropic-beta: managed-agents-2026-04-01`.

## The 4-resource model

| Resource | What it is | Create via |
|---|---|---|
| **Agent** | Versioned config: `{name, model, system, tools[], mcp_servers?, multiagent?, metadata?}` | `POST /v1/agents` |
| **Environment** | Container template: `{name, config:{type:"cloud", networking, packages?}}` | `POST /v1/environments` |
| **Session** | Running instance: `{agent:<id>, environment_id:<id>, resources?[]}` | `POST /v1/sessions` |
| **Events** | The wire: `user.*` / `agent.*` / `session.*` over SSE | `GET …/events/stream` + `POST …/events` |

## Agent config shape

The YAML files in `examples/` map **1:1** to the `POST /v1/agents` JSON body. Minimal:

```yaml
name: my-agent
model: claude-opus-4-8
system: |
  <prompt — keep long prompts in prompts/*.md and read them in deploy.py>
tools:
  - type: agent_toolset_20260401          # built-in sandbox tools
    default_config: { enabled: false }    # deny-by-default, then allowlist:
    configs: [{name: read, enabled: true}, {name: grep, enabled: true}]
  - type: mcp_toolset
    mcp_server_name: claims-admin
    default_config: { enabled: false, permission_policy: {type: always_allow} } # see gotchas #2 + #4
    configs: [{name: get_claim, enabled: true}]    # allowlist the reads; everything else is denied
mcp_servers:
  - { type: url, name: claims-admin, url: https://YOUR-DOMAIN/mcp }
multiagent:                               # orchestrators only — sub-agents must exist first
  type: coordinator
  agents: [{type: agent, id: agt_..., version: 1}]
metadata: { owner: <you>, workflow: <name>, role: Orchestrator|Reader|Writer }  # free-form; convention only
```

## Deploy recipe (what `deploy.py` does)

1. `POST /v1/agents` for each sub-agent → capture `{id, version}`
2. `POST /v1/agents` for the orchestrator with `multiagent.agents` populated from step 1
3. `POST /v1/environments` → capture `environment_id`
4. `POST /v1/sessions {agent, environment_id}`
5. **Open** `GET /v1/sessions/:id/events/stream` (SSE)
6. **Then** `POST /v1/sessions/:id/events {events:[{type:"user.message", content:[{type:"text", text:"…"}]}]}`
7. Verify: `GET /v1/agents/:id` and confirm `multiagent` is populated (API silently drops unknown fields)

## Top gotchas

1. **Open the SSE stream BEFORE posting the first event.** Session-create only provisions the container; nothing runs until an event arrives, and POST-before-stream means you miss early `agent.*` events. This is the #1 failure mode.
2. **MCP toolsets default to `permission_policy: always_ask`** (built-in `agent_toolset` defaults to `always_allow`). Forget to override and the session stalls at `stop_reason: requires_action`. Fix: set `default_config.permission_policy: {type: always_allow}` on every `mcp_toolset`.
3. **`user.message.content` must be an array of content blocks**, not a bare string. Also: agent updates require `{"version": N, …}` in the body (optimistic concurrency); the roster field is `multiagent` — older `callable_agents` is silently ignored.
4. **MCP toolsets are allow-by-default (`default_config.enabled` defaults to `true`).** A blocklist of mutators therefore fails *open*: any write tool you didn't know to name is silently callable, and real servers add tools over time. Every example in this kit sets `default_config.enabled: false` and **allowlists the reads** — the only direction that fails closed. Get the tool names from `tools/list` against your server; `MCP-SERVERS.md` has the curl recipe and the live tool inventory for every workshop mock.
5. **The human-in-the-loop answer event is `user.tool_confirmation` — `user.tool_approval` does NOT exist** (the API rejects it: `events[0].type … is not a valid value`). The whole contract, verified against the live API: an `always_ask` tool call arrives as a normal `agent.tool_use` / `agent.mcp_tool_use` event with **`evaluated_permission: "ask"`** and no result; the park arrives as **`session.status_idle`** with `stop_reason: {type: "requires_action", event_ids: ["<that event's sevt_… id>"]}` (there is no `agent.tool_use_request` or `session.requires_action` event, and the session's *status* stays `"idle"`); you answer with `{"type":"user.tool_confirmation","tool_use_id":"<that sevt_… id>","result":"allow"|"deny"}` and **keep reading the same stream**. Corollary — the one that bites: **never treat a bare `session.status_idle` as "done"; check `stop_reason.type` first**, or your client exits at the exact moment a human is supposed to act. `run.py` is the reference implementation; `examples/service/add-vehicle.yaml`'s footer is the annotated round-trip.

## Architecture convention — 3-tier least-privilege

- **Orchestrator**: Read/Grep only. Delegates; never writes, never holds Bash.
- **Reader** sub-agents: Read + read-only MCP tools. No Write. Parse untrusted inputs here.
- **Writer** sub-agent (exactly one): Write/Edit/Bash. No MCP. All production output goes through it.
- System prompts enforce: *agent recommends, doesn't decide* — outputs are drafts for human sign-off.

## When the user asks to build an agent

**Prefer the `/new-agent` skill** (it ships in this repo at `.claude/skills/new-agent/` and loads automatically). It is the guided, interview-driven version of the steps below: it asks what the agent does, which systems and tools it reads, whether an action needs a human gate, whether it needs the manual (a read-only memory store), and who owns the rubric — then writes the fully-commented example YAML, **shows it to the user before anything deploys**, and runs `validate.py` → `deploy.py --dry-run` → `deploy.py` → `run.py --ui`. It generates config; it never calls the API itself. The skill is **fully self-contained** — `.claude/skills/new-agent/` bundles its own copies of `deploy.py`, `validate.py`, `run.py`, and the tool inventory under `scripts/` and `references/`, so it also works installed standalone (`cp -R .claude/skills/new-agent ~/.claude/skills/`) in any repo. ⚠️ Those bundled files are point-in-time COPIES: **if you change `deploy.py`, `run.py`, `validate.py`, or `MCP-SERVERS.md`, re-publish the bundle** or it will drift. If you are building an agent by hand instead:

1. **Match the user's ask to a pillar (claims / service / sales) first, then the closest example.** Copy it; don't write configs from scratch.
   - **claims/**
     - `fnol-triage.yaml` — teaches: first agent — single agent, one MCP, deny-by-default toolset, the gotchas
     - `coverage-determination.yaml` + `coverage-determination-rubric.md` — teaches: a determination grounded in the ACTUAL policy form — three MCP servers including the `policy-admin` (index) → `documents` (content) hop; the hard rule that every conclusion must quote the provision it relies on; an outcomes rubric a coverage counsel owns
     - `next-best-action.yaml` + `next-best-action-rubric.md` — teaches: "trained on the claims manual" = a READ-ONLY memory store (`run.py --readonly-store`, exact literal `read_only`) beside the workflow's read-write learnings store; an outcomes rubric a claims SUPERVISOR owns; and exactly ONE executable action, gated behind `always_ask`
     - `siu-referral.yaml` — teaches: memory store (learns fraud patterns) + human-in-loop write (`refer_to_siu` → `requires_action`)
     - `adjudication.yaml` + `adjudication-rubric.md` — teaches: multi-agent 3-tier + outcomes rubric (self-graded decision memo). Runs 3-of-3 MCP servers (`documents` is live)
   - **service/**
     - `coverage-explainer.yaml` — teaches: first agent + memory store attached at session-create via `resources[]`
     - `add-vehicle.yaml` — teaches: human-in-the-loop write — `always_ask` → handle `requires_action`
     - `household-review.yaml` — teaches: multi-agent — 3-tier orchestration (readers / writer)
   - **sales/**
     - `quote-builder.yaml` — teaches: multiple MCP servers, each with its own deny-by-default read allowlist
     - `renewal-retention.yaml` — teaches: outcomes rubric — agent self-grades its own output
2. Edit the YAML; keep tool grants minimal per the 3-tier pattern above, and keep every `mcp_toolset` on `default_config.enabled: false` + a read allowlist (gotcha #4) — never a mutator blocklist.
   - After ANY change to an allowlist or an MCP url, run **`python3 validate.py`** — it asserts every granted tool name exists on the LIVE server that example points at. A deny-by-default allowlist with a stale tool name fails closed and SILENTLY: the agent just can't call it. validate.py is the only thing that tells you.
3. Set `metadata.owner` / `workflow` / `role` — shared orgs fill fast and unlabeled agents get lost.
4. `python deploy.py <file.yaml>` — creates the agent, prints `agt_...`. Then `python run.py --agent agt_... "<instruction>"` — creates a session, opens SSE, streams events. **deploy.py defines, run.py invokes.** In production, run.py becomes a webhook handler / cron / UI action.
   - **Verify what actually got deployed**: `GET /v1/agents/:id` returns the full config the API is holding — diff it against `deploy.py --dry-run <file.yaml>`. Since the API silently drops unknown fields (gotcha #3), this round-trip diff is how you catch a typo'd field name. Cleanup is `POST /v1/agents/:id/archive` (not DELETE — there is no DELETE).
5. Memory stores attach at **session-create** via `resources[]`, not on the agent — `run.py --memory-store memstore_...` does this; see `service/coverage-explainer.yaml` footer and `docs/memory-best-practices.md`.

## Going deeper

For API details beyond this kit (memory stores, vaults, outcomes, dreaming, streaming reconnect, SDK code generation), invoke the **`claude-api` skill** — e.g. `/claude-api managed-agents-onboard` scaffolds the session create + SSE loop in the project's language. The skill teaches the client mechanics; this kit provides the domain-shaped configs on top.
