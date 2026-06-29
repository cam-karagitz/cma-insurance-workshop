# Claims Adjudication — Outcomes Rubric

> The grader sees **only** files under `/mnt/session/outputs/` — never the
> agent's reasoning or conversation. Grade the artifact, not the process.

Attach it with one flag — `run.py` sends it as the kickoff:

```bash
python3 run.py --agent agent_… --rubric examples/claims/adjudication-rubric.md \
  "Adjudicate claim CLM-2026-0412."
```

(Under the hood that one flag sends a single `user.define_outcome` event carrying
BOTH the instruction and this rubric — `{"type":"user.define_outcome",
"description":"<the instruction>","rubric":{"type":"text","content":"<this
file>"},"max_iterations":5}` — the same call the operations console makes. The
rubric is **not** a session-create `resources[]` entry, and it is a nested
object, not a bare string. When the grader finishes, `run.py` prints the
`outcome.result` score.)

Each criterion scores **0 / 1 / 2**. Max 10. Production bar: **≥ 8**.

## 1. Coverage position is cited
`decision-memo.md` states the coverage position and cites the policy form
section relied on. 0 = no citation; 1 = position stated, citation vague or
missing; 2 = position stated with explicit form + section cite.

## 2. Damages evaluation shows line-item support
`decision-memo.md` shows the damages evaluation per coverage line with the
supporting math/estimate source. 0 = single lump number or missing; 1 = per-
line figures without support; 2 = per-line figures each with stated basis.

## 3. Disposition is one of the allowed values with rationale
Recommended disposition is exactly one of `pay` / `partial-pay` / `deny` /
`investigate-further`, followed by a one-paragraph rationale. If `deny`, the
specific exclusion is cited and the "subject to adjuster + compliance review"
note is present. 0 = missing or off-vocabulary; 1 = valid value, weak/absent
rationale; 2 = valid value with rationale (and exclusion cite if `deny`).

## 4. Payment recommendation is complete
`payment-rec.md` names payee, coverage line, amount, deductible applied, and
reserve change. 0 = file missing; 1 = present with ≥1 element missing;
2 = all five elements present.

## 5. Human-review framing intact
`decision-memo.md` opens with `DRAFT — Adjuster Review & Authority Sign-off
Required` and includes a blank Adjuster signature / date / authority-level
block. `payment-rec.md` opens with `DRAFT — No payment issues until signed.`
0 = either header missing; 2 = both headers present and signature block
present. *(No partial credit — this is the compliance line.)*
