#!/usr/bin/env python3
"""Preflight: every MCP tool an example ALLOWLISTS must exist on the LIVE
server it points at.

WHY THIS EXISTS
Every mcp_toolset in this kit is deny-by-default with an explicit allowlist of
tool names. That is the safe direction: a tool name that is wrong, stale, or
typo'd fails CLOSED (the agent simply cannot call it) instead of failing open.
But "fails closed" still means a broken lab: an agent that silently cannot call
a tool it needs will limp through a session and nobody knows why. The original
versions of these examples shipped with tool names that did not exist on the
mock servers, and there was no way to notice short of reading every server's
source. This script is that way. Run it before every workshop.

  python3 validate.py                                  # every example
  python3 validate.py examples/claims/fnol-triage.yaml # one example

It loads each example, finds every mcp_toolset, calls tools/list on the LIVE
url that example actually points at, and asserts every granted (enabled: true)
tool name exists there. Servers whose url is still a placeholder
(your-mcp.example / YOUR-DOMAIN) are reported and skipped — you have not
pointed them at anything real yet, which is fine, and is its own reminder.

Exit 0 = clean. Exit 1 = at least one example grants a tool its live server
does not have. Requires: pyyaml (already required by deploy.py).
"""
import json
import pathlib
import sys
import urllib.error
import urllib.request

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("error: pyyaml is required (it already is, for deploy.py):  pip install pyyaml")

HERE = pathlib.Path(__file__).parent
MCP_H = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
_CACHE: dict = {}


def live_tools(url: str):
    """tools/list against a live streamable-HTTP MCP server. Cached per url."""
    if url in _CACHE:
        return _CACHE[url]
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}).encode()
    raw = urllib.request.urlopen(urllib.request.Request(url, data=body, headers=MCP_H, method="POST"),
                                 timeout=30).read().decode()
    for line in raw.splitlines():
        if line.startswith("data: "):
            _CACHE[url] = {t["name"] for t in json.loads(line[6:])["result"]["tools"]}
            return _CACHE[url]
    raise RuntimeError("the response was not a streamable-HTTP tools/list result")


def is_placeholder(url: str) -> bool:
    return (not url) or ("your-mcp.example" in url) or ("YOUR-DOMAIN" in url)


# Say EXACTLY what is being checked and where the list came from. The failure
# this prevents: running `validate.py` with no args from your own project
# directory validates the EXAMPLES THAT SHIP NEXT TO THIS SCRIPT — not your new
# file — and a "PREFLIGHT CLEAN" over the wrong files is worse than no check.
if sys.argv[1:]:
    files, src = [pathlib.Path(a) for a in sys.argv[1:]], "named on the command line"
else:
    files, src = sorted((HERE / "examples").rglob("*.yaml")), f"every example under {HERE / 'examples'}"
if not files:
    sys.exit("nothing to validate: pass the YAML path, e.g.  python3 validate.py my-agent.yaml")
print(f"preflight: {len(files)} file(s), {src}:")
for f in files:
    print(f"          {f}")
print()
fails = skips = 0
for f in files:
    try:
        docs = list(yaml.safe_load_all(f.read_text()))
    except Exception as ex:  # a YAML that does not parse is its own failure
        fails += 1
        print(f"  FAIL  {f.name:36s} does not parse: {ex}")
        continue
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        servers = {s.get("name"): s.get("url", "") for s in (doc.get("mcp_servers") or [])}
        for ts in (doc.get("tools") or []):
            if ts.get("type") != "mcp_toolset":
                continue
            name = ts.get("mcp_server_name", "?")
            granted = [c["name"] for c in (ts.get("configs") or []) if c.get("enabled") is True]
            label = f"{f.name:36s} {doc.get('name', '?'):28s} {name}"
            # A toolset whose mcp_server_name matches NO declared server is the
            # silent-dead-grant bug this script exists to catch (usually a typo).
            # It must be a FAIL, never a "skip" hiding inside a CLEAN.
            if name not in servers:
                fails += 1
                print(f"  FAIL  {label}  no mcp_servers entry is named {name!r} -- every tool in this toolset is silently UNREACHABLE")
                continue
            url = servers.get(name, "")
            if is_placeholder(url):
                skips += 1
                print(f"  SKIP  {label}  (placeholder url -- bring your own server)")
                continue
            try:
                have = live_tools(url)
            except Exception as ex:
                fails += 1
                print(f"  FAIL  {label}  live server unreachable: {ex}")
                continue
            missing = [g for g in granted if g not in have]
            if missing:
                fails += 1
                print(f"  FAIL  {label}  grants tools the LIVE server does NOT have: {missing}")
            else:
                print(f"  ok    {label}  {len(granted)} granted, all real")

print()
# Courtesy check, NOT a failure: this script and --dry-run are stdlib-only on
# purpose, so they both pass on a machine that cannot run a REAL deploy. The
# first real `deploy.py` / `run.py` call imports `requests` and dies. Say so
# now, at preflight time, not on workshop day.
try:
    import requests  # noqa: F401
except ImportError:
    print("WARNING: `requests` is not installed for this python. validate.py and")
    print("`deploy.py --dry-run` do not need it -- but a REAL `deploy.py` or `run.py`")
    print("call DOES, and it will die with ModuleNotFoundError. Fix it now (PREREQS.md):")
    print("    python3 -m venv .venv && .venv/bin/pip install pyyaml requests\n")
if fails:
    print(f"PREFLIGHT FAILED ({fails}) -- a granted tool name does not exist on its live server.")
    print("Fix the names above before workshop day; deny-by-default means those grants are silently dead.")
    sys.exit(1)
print(f"PREFLIGHT CLEAN -- every granted tool exists on its live server. ({skips} placeholder toolset(s) skipped.)")
