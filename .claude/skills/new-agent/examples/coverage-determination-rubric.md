# Coverage Determination — Outcomes Rubric

> The grader sees **only** `/mnt/session/outputs/coverage-position.md` — never
> the agent's reasoning, tool calls, or the policy form itself. It grades the
> **form** of the memo. Whether a quoted provision is *faithful* to the
> contract is your coverage counsel's spot-check, and it is one
> `documents/get_document` call away — that division of labor (the machine
> checks structure, your expert checks truth) is the design, say it out loud.
>
> **This rubric belongs to coverage counsel.** Edit a criterion in the room,
> rerun the same claim, and watch the score change.

Attach it with one flag — `run.py` sends it as the kickoff:

```bash
python3 run.py --agent agent_… --rubric examples/claims/coverage-determination-rubric.md \
  "Determine coverage for claim CLM-2026-0419."
```

(Under the hood that one flag sends a single `user.define_outcome` event carrying
BOTH the instruction and this rubric — `{"type":"user.define_outcome",
"description":"<the instruction>","rubric":{"type":"text","content":"<this
file>"},"max_iterations":5}` — the same call the operations console makes. The
rubric is **not** a session-create `resources[]` entry, and it is a nested
object, not a bare string. When the grader finishes, `run.py` prints the
`outcome.result` score.)

Each criterion scores **0 / 1 / 2** unless noted. Max 10. Production bar: **≥ 8**.

## 1. Every determination is cited AND quoted
Each Coverage Analysis sub-section carries a CITATION naming the form number,
section title, and paragraph, AND a set-off, verbatim-style quotation of the
provision relied on. 0 = any determination with neither; 1 = citations present
but ≥1 is vague ("the policy says…") or the "quote" is a paraphrase not set
off as quoted text; 2 = every determination has a specific cite and a set-off
quote. *A determination that does not cite the section it relies on is not a
determination; it is an opinion.*

## 2. The open-peril method is applied correctly
For a dwelling loss on an open-peril form, the analysis reasons from "direct
physical loss is covered unless a provision takes it away" and identifies what
(if anything) takes it away. 0 = the memo hunts for the peril in a list of
covered perils, or asserts coverage with no method at all; 1 = the conclusion
is right but the method is not stated; 2 = the open-peril structure is stated
and drives the analysis.

## 3. Exclusions are read whole — carve-backs addressed
Where an exclusion is raised, the memo addresses whether an exception or
carve-back *within that exclusion* restores coverage, before concluding.
0 = an exclusion is applied with no mention of its exceptions; 1 = the
carve-back is mentioned but not analyzed against the facts; 2 = the carve-back
is quoted and applied to the facts. *(Half-quoting an exclusion produces the
wrong answer, and is the single most common failure of a coverage memo.)*

## 4. Coverage and settlement are separated
"Is it covered?" and "how is it settled?" are answered as distinct questions:
loss-settlement limitations (e.g. an actual-cash-value method for older roof
surfacing) appear under `## Settlement Considerations`, not presented as an
exclusion. 0 = the two are conflated, or settlement is ignored where the form
plainly addresses it; 1 = both are addressed but mixed together; 2 = cleanly
separated, with the settlement provision cited.

## 5. Human-review framing intact — 0 / 2
`coverage-position.md` exists at the exact path, contains every required `##`
heading verbatim, ends with `## DRAFT — Coverage Counsel & Adjuster Review
Required`, never uses the word "denied" as a final disposition (a does-not-
cover conclusion is framed as a recommendation for counsel review), and any
unresolved question (e.g. causation pending an engineer report) is marked
INSUFFICIENT INFORMATION rather than forced. 0 = any of these is violated;
2 = all hold. *(No partial credit — this is the compliance line.)*

---

**Total: /10.** Target ≥ 8 for a memo an adjuster can act on.
