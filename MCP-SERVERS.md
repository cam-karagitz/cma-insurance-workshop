# MCP Servers — workshop mocks & how to swap in your own

The example YAMLs ship pointing at **hosted mock MCP servers** so they run out of the box on workshop day. The mocks serve synthetic insurance data — fake policies, claims, customers. Nothing real, no auth, reachable from anywhere (including CMA's hosted containers).

**To swap in your own:** edit the `url:` line under `mcp_servers:` in the YAML. The `name:` must match the `mcp_server_name:` in the corresponding `mcp_toolset` block — leave the name alone unless you're also renaming the toolset. Then **rebuild the allowlist**: run `tools/list` against your server and name the read tools the agent actually needs (curl recipe below).

## How the examples grant tools — deny-by-default, allowlist the reads

Every `mcp_toolset` in this kit uses the same shape:

```yaml
- type: mcp_toolset
  mcp_server_name: claims-admin
  default_config:
    enabled: false                              # 1) nothing is callable…
    permission_policy: { type: always_allow }   # 2) …and what IS doesn't stall
  configs:
    - { name: get_claim,       enabled: true }  # 3) …except what you name
    - { name: get_open_claims, enabled: true }
```

**1) Deny-by-default.** With `default_config.enabled: false`, a tool is callable only if a `configs:` entry sets `enabled: true`. This is the load-bearing line.

Do **not** use the other direction — `enabled: true` plus a blocklist of mutators. A blocklist fails **open**: any write tool you didn't know to name is silently callable, and real MCP servers add tools over time. An allowlist fails **closed**: a tool the server ships next month arrives disabled until you opt it in.

To make it concrete: an earlier revision of `claims/adjudication.yaml` blocklisted five claims-admin mutators by name — none of which existed on the workshop mock — while the mock's *actual* write tool, `file_fnol`, was missing from the list and wide open. The blocklist *looked* careful and protected nothing. Deny-by-default makes that entire class of mistake impossible.

**2) `always_allow` override.** MCP toolsets default to `permission_policy: always_ask` (the built-in `agent_toolset` defaults to `always_allow`). Forget this and the first MCP call parks the session at `stop_reason: requires_action`. Set it on every `mcp_toolset`.

**3) Allowlist by name.** Grant the read tools the agent's job needs — get the list from `tools/list` against the real server. The one deliberate exception is a human-in-the-loop write, which is *enabled* **and** flipped to a per-tool `always_ask` so the session pauses for approval (`service/add-vehicle.yaml`, `claims/siu-referral.yaml`). The pause is the feature.

## The workshop mocks (all live, no auth)

Base URL: `https://ins-mocks.vercel.app/<name>/mcp`

All seven share one coherent fictional world — the same households, agents, policies, and claims across every system — so multi-MCP examples just work. Writes persist to a shared overlay you can reset at `https://ins-mocks.vercel.app/admin`.

| MCP `name` | Stands in for | Read tools | Write tools | Used by examples |
|---|---|---|---|---|
| `claims-admin` | ClaimCenter | `get_claim`, `get_claims_by_household`, `get_claims_by_policy`, `get_open_claims`, `get_cat_event_claims` | `file_fnol`, `refer_to_siu` | `claims/*` |
| `policy-admin` | PolicyCenter | `get_policy`, `get_policies_by_household`, `get_coverage_summary`, `get_renewal_pipeline`, `get_property_detail`, `get_documents`, `rate_endorsement` | `request_id_card`, `endorse_policy` | `claims/siu-referral`, `claims/adjudication`, `service/*`, `sales/renewal-retention` |
| `crm` | Salesforce agency CRM | `get_household`, `search_households`, `get_book_of_business`, `get_activities`, `get_life_events`, `get_opportunities` | `update_contact_info`, `escalate_to_agent` | `service/household-review` |
| `billing` | BillingCenter | `get_billing_account`, `get_payment_history`, `get_delinquencies`, `get_invoice_schedule` | — | *(none yet — free for your own builds)* |
| `quoting` | Rating / quote platform | `get_quote`, `get_quotes_by_household`, `get_open_quote_pipeline`, `explain_rate_factors` | — | *(none yet)* |
| `uw-workbench` | Submission / UW queue | `get_submission`, `get_uw_queue`, `get_appetite_rules`, `evaluate_risk` | — | *(none yet)* |
| `gl` | General ledger | `get_chart_of_accounts`, `get_trial_balance`, `get_journal_entries`, `get_budget`, `get_open_accruals` | — | *(none yet)* |

The four "none yet" servers exist for **your** builds during the lab — a billing-delinquency agent, a submission-triage agent, a premium reconciliation. Same world, same households, no extra setup.

Verify any of them yourself — plain curl, no auth:

```bash
curl -s -X POST https://ins-mocks.vercel.app/claims-admin/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

> ⚠️ **Shared state.** All attendees share one mock overlay; concurrent writes are visible to everyone. The deny-by-default configs mean almost no writes are reachable anyway, and the two HITL examples keep theirs behind `always_ask`. Reset the overlay between runs at `/admin`.

## The human-in-the-loop labs run live against the workshop mocks

Both HITL examples exercise their gated write end-to-end against `ins-mocks` — no swap-in required.

- **`claims/siu-referral` → `refer_to_siu`** on `claims-admin`. The session parks at `requires_action`; on approval the referral lands ON the claim record, so `get_claim` immediately shows a structured `siuReferral` block plus an `SIU Intake` note. Idempotent: re-referring an already-referred claim returns the existing referral — concurrent attendees never duplicate.
- **`service/add-vehicle` → `rate_endorsement` + `endorse_policy`** on `policy-admin`. The full GATHER → RATE → PRESENT → PAUSE → APPLY loop runs live, and the endorsed policy (new vehicle, endorsement row, bumped premium) is immediately visible in `get_policy` and `get_coverage_summary`.
  - **Deliberate demo hook:** rate a vehicle with `primary_use: business` or `annual_mileage > 25000` and `rate_endorsement` returns a non-null `referral`. The example's system prompt instructs the agent to STOP and route to underwriting — *without ever reaching the `endorse_policy` gate*. Two distinct human gates, demonstrable in one lab.

> **Why these tools were added (a true war story for the room).** They landed on the mocks on 2026-06-29 — *after* the example configs were flipped to deny-by-default. Under the original blocklist configs, the moment `refer_to_siu` deployed it would have been silently callable by `fnol-triage` and the `adjudication` reader: no blocklist named it, because it did not exist when those blocklists were written. Under deny-by-default it arrived disabled everywhere except the one agent that explicitly grants it. *"What happens when the server adds a mutator?"* stopped being a hypothetical the same day the fix shipped.

## Mocks not yet available — bring your own (or stub)

| MCP `name` | Needed by | What it should expose | Stand-in for workshop day |
|---|---|---|---|
| `documents` | `claims/adjudication` | `get_document`, `list_attachments` (claim photos, police reports, estimates) | `claims-admin`'s `get_claim` returns the loss description + adjuster-notes timeline; run adjudication with 2 of 3 servers |
| `vehicle-data` | `sales/quote-builder` | `decode_vin`, `get_symbol`, `get_safety_rating` | Inline a hardcoded vehicle in the system prompt for the demo |
| `driver-history` | `sales/quote-builder` | `lookup_mvr`, `lookup_clue` | Inline a clean-record assumption in the system prompt |
| `rating-engine` | `sales/quote-builder` | `rate_risk(coverage, profile) → premium` | The hardest to fake — consider making `quote-builder` a "discuss the structure" lab rather than a live run, or stub a flat-rate response |
| `market-intel` | `sales/renewal-retention` | `get_competitor_rates`, `get_churn_signals` | Inline a sample competitor-rate table in the system prompt |

## Building your own MCP server

CMA agents connect to **remote streamable-HTTP MCP servers** (not stdio). The fastest path:

- **Node/Vercel**: `npm create mcp-server@latest` → deploy to Vercel → URL goes straight into `mcp_servers[].url`
- **Python**: `pip install fastmcp` → `FastMCP(..., transport="streamable-http")` → deploy anywhere that serves HTTP
- Docs: https://modelcontextprotocol.io/docs/concepts/transports#streamable-http

Once deployed: run `tools/list` (curl above), build the read allowlist from the result, and the swap is one `url:` line per example.
