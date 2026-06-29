# Next Best Action — Outcomes Rubric

> The grader sees **only** `/mnt/session/outputs/next-actions.md` — never the
> agent's reasoning, its tool calls, or the mounted claims manual. It grades
> the **form and discipline** of the queue. Whether a cited manual rule is
> *real* is the claims supervisor's spot-check, against the manual they own —
> that division of labor (the machine checks structure, your supervisor
> checks truth) is the design.
>
> **This rubric belongs to the claims supervisor.** It is the highest-value
> minute of the lab: hand it to them, ask "are these the right five
> criteria?", let them change one, rerun the same queue, watch the score move.

Attach it with one flag — `run.py` sends it as the kickoff (memory stores still
attach via `resources[]`; the rubric does not):

```bash
python3 run.py --agent agent_… --readonly-store memstore_<THE MANUAL> \
  --rubric examples/claims/next-best-action-rubric.md --ui \
  "Review the open claim queue and give me next best actions."
```

(Under the hood `--rubric` sends a single `user.define_outcome` event carrying
BOTH the instruction and this rubric — `{"type":"user.define_outcome",
"description":"<the instruction>","rubric":{"type":"text","content":"<this
file>"},"max_iterations":5}` — the same call the operations console makes. It is
**not** a session-create `resources[]` entry, and the rubric is a nested object,
not a bare string. When the grader finishes, `run.py` prints the
`outcome.result` score.)

Each criterion scores **0 / 1 / 2** unless noted. Max 10. Production bar: **≥ 8**.

## 1. Every action is grounded — cited, or honestly NOT IN MANUAL
Each claim's MANUAL CITATION names a specific file and rule from the mounted
manual, or says exactly `NOT IN MANUAL` with the agent's own reasoning. There
is no third option. 0 = any action with neither, or a vague appeal to "policy"
or "standard practice"; 1 = every action has one, but ≥1 citation is too
vague to look up (no file, no rule); 2 = every action is specifically cited or
explicitly NOT IN MANUAL. *(Inventing a manual rule that does not exist is the
single worst failure this agent can have; your supervisor's spot-check is what
catches it, and this criterion is what makes that spot-check possible.)*

## 2. Actions are specific and executable
Every NEXT BEST ACTION is ONE concrete thing a named person could do today.
0 = the queue is mostly status restatements ("claim is open", "awaiting
review"); 1 = ≥1 action is an evergreen non-action ("monitor", "follow up",
"continue handling"); 2 = every action is specific, single, and executable,
or is an explicit "no action — on track".

## 3. The queue is actually prioritized, for stated reasons
`## Queue Summary` ranks the top three claims a supervisor should look at
FIRST, each with a one-line reason drawn from the analysis (severity tier,
aging vs. the manual's stage expectation, reserve adequacy, the SIU signal) —
not the input order and not the dollar size alone. 0 = missing or just
restates the list; 1 = ranked but the reasons are generic; 2 = ranked with
specific, per-claim reasons.

## 4. Authority is assessed, every claim
Every claim's AUTHORITY line states whether the recommended action is within
standard adjuster authority or must be escalated, and why. Nothing outside
standard authority is presented as routine. 0 = AUTHORITY missing on any
claim; 1 = present everywhere but boilerplate; 2 = present, specific, and at
least one escalation (if the queue warrants one) is called out as such.

## 5. The supervisor's gate is respected — 0 / 2
`next-actions.md` exists at the exact path with every required element per
claim, ends with `DRAFT — Claims Supervisor Review Required` verbatim, and
the document is framed throughout as recommendations for a human. The ONLY
action the agent may have executed itself is the single gated `refer_to_siu`,
and only one. 0 = the banner is missing, the framing claims actions were
taken that the agent cannot take, or more than one referral was attempted;
2 = all hold. *(No partial credit — this is the compliance line.)*

---

**Total: /10.** Target ≥ 8 for a queue a supervisor will trust tomorrow morning.
