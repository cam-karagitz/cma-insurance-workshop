# Claims Adjudication — Outcomes Rubric

> The grader sees **only** files under `/mnt/session/outputs/` — never the
> agent's reasoning or conversation. Grade the artifact, not the process.

Attach at session-create alongside the agent (see footer of `adjudication.yaml`):

```json
"resources": [{
  "type": "outcome",
  "rubric": "<contents of this file>",
  "output_glob": "/mnt/session/outputs/**"
}]
```

Each criterion scores **0 / 1 / 2**. Max 10. Production bar: **≥ 8**.

## 1. Coverage analysis is grounded
`decision-memo.md` cites the specific policy form + section for every coverage
position taken (e.g., "ISO PA 00 01 §B.2"). 0 = no citations; 1 = some
positions cited; 2 = every coverage statement has a form+section cite.

## 2. Liability assessment states a percentage and basis
A liability split (e.g., "70/30 adverse") with at least two facts supporting
it. 0 = missing; 1 = percentage without basis or basis without percentage;
2 = both present.

## 3. Reserve recommendation is a range with assumptions
`payment-rec.md` gives a low–high reserve range and lists the assumptions
driving each bound. 0 = single number or missing; 1 = range without
assumptions; 2 = range with explicit assumptions for both bounds.

## 4. Disposition is one of the allowed values with next step
One of PAY / DENY-RECOMMEND / INVESTIGATE / SUBRO-REFER, plus a concrete
next action and owner. 0 = missing or invalid value; 1 = valid value, vague
next step; 2 = valid value with specific next action + owner.

## 5. Human-review framing intact
Both files carry "DRAFT — Adjuster Review Required" and the memo never
asserts a final decision. 0 = framing missing on either file; 2 = present
on both. *(No partial credit — this is the compliance line.)*
