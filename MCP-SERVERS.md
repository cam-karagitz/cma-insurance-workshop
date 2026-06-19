# MCP Servers — workshop mocks & how to swap in your own

The example YAMLs ship pointing at **hosted mock MCP servers** so they run out of the box on workshop day. The mocks serve synthetic insurance data — fake policies, claims, customers. Nothing real.

**To swap in your own:** edit the `url:` line under `mcp_servers:` in the YAML. That's it. The `name:` must match the `mcp_server_name:` in the corresponding `mcp_toolset` block — leave the name alone unless you're also renaming the toolset.

## Mocks available now

| MCP `name` | Workshop mock URL | Exposes (read tools) | Write tools (blocklisted in examples) | Used by |
|---|---|---|---|---|
| `claims-admin` | `https://ins-mocks.vercel.app/claims-admin/mcp` | `get_claim`, `list_claims`, `get_loss_details` | `file_fnol`, `update_reserve`, `assign_adjuster` | `claims/fnol-triage`, `claims/adjudication` |
| `policy-admin` | `https://ins-mocks.vercel.app/policy-admin/mcp` | `get_policy`, `get_coverage`, `rate_endorsement`, `lookup_vin` | `endorse_policy`, `cancel_policy`, `update_insured` | `service/*`, `claims/adjudication`, `sales/renewal-retention` |

These two cover **4 of the 6 examples end-to-end** (`claims/fnol-triage`, `service/coverage-explainer`, `service/add-vehicle`, and `claims/adjudication` minus its `documents` server).

> ⚠️ **Shared state**: the mocks back writes with a shared KV overlay. If multiple workshop attendees call write tools (e.g. `endorse_policy` in `service/add-vehicle`) they'll see each other's changes. For the workshop, either keep writes behind `always_ask` (the example default) or namespace by using distinct fixture IDs per attendee.

## Mocks not yet available — bring your own (or stub)

| MCP `name` | Needed by | What it should expose | Stand-in for workshop day |
|---|---|---|---|
| `documents` | `claims/adjudication` | `get_document`, `list_attachments` (claim photos, police reports, estimates) | Point at `claims-admin` and use `get_loss_details` as a proxy, or leave the placeholder and run adjudication with 2 of 3 servers |
| `vehicle-data` | `sales/quote-builder` | `decode_vin`, `get_symbol`, `get_safety_rating` | Inline a hardcoded vehicle in the system prompt for the demo |
| `driver-history` | `sales/quote-builder` | `lookup_mvr`, `lookup_clue` | Inline a clean-record assumption in the system prompt |
| `rating-engine` | `sales/quote-builder` | `rate_quote(coverage, risk) → premium` | The hardest to fake — consider making `quote-builder` a "discuss the structure" lab rather than a live run, or stub a flat-rate response |
| `market-intel` | `sales/renewal-retention` | `get_competitor_rates`, `get_churn_signals` | Inline a sample competitor-rate table in the system prompt |

## Building your own MCP server

CMA agents connect to **remote streamable-HTTP MCP servers** (not stdio). The fastest path:

- **Node/Vercel**: `npm create mcp-server@latest` → deploy to Vercel → URL goes straight into `mcp_servers[].url`
- **Python**: `pip install fastmcp` → `FastMCP(..., transport="streamable-http")` → deploy anywhere that serves HTTP
- Docs: https://modelcontextprotocol.io/docs/concepts/transports#streamable-http

Once deployed, the swap is one line per example.
