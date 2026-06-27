# SDD: Judge Row Completeness For Empty And Failed Answers

Status: proposed for immediate implementation.
Date: 2026-06-27.
Scope: `judge.py`, judged JSONL rows, CEOps run-quality reporting.

## 1. Scope Honesty

This SDD does **not** change model inference, judge prompts, judge scores, or the
scientific interpretation of a DNF. It changes the judged-row contract so every
row has the same evidence fields, including rows for empty answers.

The observed problem is narrow: zero-output `DNF:stall` answers are scored as
`score=1` and `verdict=empty`, but the output row lacks `evidence`,
`criteria_met`, and `criteria_missed`. That makes reports look like the judge row
is malformed when it is really an intentionally empty-answer judgment.

## 2. User-Visible Outcome

After this change, any row in `judged.<RUN_ID>.jsonl` has these fields:

```text
score
evidence
verdict
criteria_met
criteria_missed
```

For an empty answer, the row should be explicit:

```json
{
  "score": 1,
  "evidence": "No answer text was available for judging; the inference row did not produce a completion.",
  "verdict": "empty",
  "criteria_met": [],
  "criteria_missed": ["answer was empty or unavailable"]
}
```

This lets the dashboard and later reports distinguish **empty answer** from
**missing judge metadata**.

## 3. Evidence

The `spread10` OKF-v1 child run showed 18 judge rows with `score=1` and
`verdict=empty` but without `evidence`, `criteria_met`, or `criteria_missed`.
Those rows corresponded to zero-output `DNF:stall` inference rows.

The inference rows were structurally complete: 129/129 fields present. The gap is
only in the judge-row normalization path.

## 4. Decision

Add a single normalization function in `judge.py`:

```text
normalize_judgement(...)
```

Use it for:

1. Empty-answer rows before any judge call.
2. Parse-error fallback rows from `judge_one()`.
3. Any judge JSON that omits optional-but-contractual detail fields.

Do not retry or re-score historical rows in this SDD. Existing partial run rows
remain historical evidence; future judge output becomes schema-stable.

## 5. Contract

- `score` remains whatever the judge assigned, except empty answers get `1`.
- `verdict` is always a non-empty string.
- `evidence` is always a non-empty string.
- `criteria_met` is always a list.
- `criteria_missed` is always a list.
- Non-standard judge fields are preserved.

## 6. Rejected Alternatives

| Alternative | Rejected because |
|---|---|
| Leave empty rows sparse | Downstream reports cannot tell sparse-by-design from corrupted judge output. |
| Drop empty-answer judge rows | Hides DNF reliability from judge completeness and paper/report counts. |
| Re-run judges for empty answers | Wasteful; there is no answer text to evaluate. The correct evidence is synthetic and explicit. |
| Patch reports only | Leaves the canonical JSONL artifact inconsistent. |

## 7. Validation

Add a stdlib regression test that proves:

1. Empty-answer normalization emits all five detail fields.
2. Partial judge JSON is completed with empty criteria lists.
3. Parse-error fallback from `judge_one()` still satisfies the same contract.
