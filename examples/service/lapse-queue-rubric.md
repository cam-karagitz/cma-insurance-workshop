# Lapse Queue — Outcomes Rubric

> The grader sees **only** `/mnt/session/outputs/lapse-queue.md` — never the
> agent's reasoning, its tool calls, or the billing system itself. It grades
> the **form** of the queue. Whether a past-due amount or a lapse date is
> *faithful* to the billing system is your retention manager's spot-check,
> and it is one `billing/get_billing_account` call away — that division of
> labor (the machine checks structure, your manager checks truth) is the
> design, say it out loud. It is also why the agent is required to *write its
> evidence into the artifact*: the `## Completeness Check` counts and the
> `LAST CONTACT` line on every entry exist so the grader can score 1 and 4
> from the document alone.
>
> **This rubric belongs to the retention / service manager.** Edit a
> criterion in the room, rerun the same morning's queue, and watch the score
> change. They wrote these five things; the agent did not.

Attach it with one flag — `run.py` sends it as the kickoff:

```bash
python3 run.py --agent agt_… --rubric examples/service/lapse-queue-rubric.md --ui \
  "Build this morning's lapse outreach queue. Lookback for recent contact: 7 days."
```

(Under the hood that one flag sends a single `user.define_outcome` event carrying
BOTH the instruction and this rubric — `{"type":"user.define_outcome",
"description":"<the instruction>","rubric":{"type":"text","content":"<this
file>"},"max_iterations":5}` — the same call the operations console makes. The
rubric is **not** a session-create `resources[]` entry, and it is a nested
object, not a bare string. When the grader finishes, `run.py` prints the
`outcome.result` score.)

Each criterion scores **0 / 1 / 2** unless noted. Max 10. Production bar: **≥ 8**.

## 1. Every delinquent household in the window is accounted for
The `## Completeness Check` states how many accounts `get_delinquencies`
returned, how many entries the `## Outreach Queue` contains, and either
`MATCH` or an explicit `UNRESOLVED` list. The queue entry count agrees with
the stated count. 0 = the section is missing, the counts disagree with no
explanation, or any account was silently dropped; 1 = the section is present
but a count is missing, or unresolved accounts are mentioned without being
individually listed; 2 = both counts stated, they reconcile, and every
unresolved account (if any) is named. *A retention queue that quietly loses
a household is worse than no queue at all — that household lapses unworked.*

## 2. The priority order is justified by the data
The queue is ordered most-urgent-first, and every entry's `URGENCY` line
states the *data* that earned its rank — days to lapse, premium at risk,
policy count — not a vibe. No entry is marked `URGENT` without naming its
days-to-lapse and what is lost. 0 = no discernible order, or `URGENT` is
asserted with no figures; 1 = an order exists but ≥1 ranking is unexplained,
or an `URGENT` entry is missing a required figure; 2 = the order is stated,
every `URGENCY` line carries its figures, and a reader could re-derive the
ranking from the document alone. *"It felt urgent" is not a reason a manager
can defend.*

## 3. Every outreach recommendation is specific to that household
Every non-`HOLD` entry's `OUTREACH` line names ONE channel and a talking
point built from *that household's* facts already shown in its own entry —
what they lose, by when, for how much. 0 = any recommendation is a generic
script ("call to discuss payment options"), names no channel, or cites a
fact that appears nowhere in the entry; 1 = recommendations are specific but
≥1 reads as boilerplate reusable on a different household unchanged; 2 =
every recommendation could only have been written for its own household.
*If you could swap two talking points between households and nobody would
notice, the agent didn't do the work.*

## 4. No double-contact — and the check is shown
EVERY entry carries a `LAST CONTACT` line stating what the CRM activity
check returned (a dated contact, or the exact words `NO RECENT CONTACT ON
FILE`). No entry whose `LAST CONTACT` falls inside the lookback carries an
outreach recommendation — it is `HOLD`, and it is not in `## Escalations`.
0 = any entry is missing its `LAST CONTACT` line, or a recently-contacted
household is recommended for outreach or escalation; 1 = the check is shown
on every entry but ≥1 recently-contacted household is not clearly marked
`HOLD`; 2 = the check is visible on every entry and no recently-contacted
household is recommended or escalated. *(The grader cannot see the CRM —
which is exactly why the agent must show its receipt on every line.)*

## 5. Human-review framing intact, and the only action is the gated one — 0 / 2
`lapse-queue.md` exists at the exact path, contains the three `##` headings
`## Outreach Queue`, `## Escalations`, and `## Completeness Check` verbatim,
frames every outreach as a recommendation for a human, and ends with
`DRAFT — Retention Manager Review Required`. `## Escalations` lists only
households marked `URGENT`, and the document never claims, implies, or
instructs anything beyond the one gated `escalate_to_agent` action (no
"I updated the contact record", no "I emailed the household", no payment
taken, no policy changed). 0 = any of these is violated; 2 = all hold.
*(No partial credit — this is the compliance line.)*

---

**Total: /10.** Target ≥ 8 for a queue the retention lead can work without
re-checking every line.
