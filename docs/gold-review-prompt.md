# Gold Review Prompt (Draft)

Use this prompt to run adversarial review of scenario gold answers, rubrics, and
checks before submission.

## Purpose

- Detect gameable deterministic checks
- Detect false-fail patterns (especially negation-sensitive rules)
- Detect rubric-answer mismatches

## Minimal review checklist

1. Does the gold answer directly resolve the scenario question?
2. Could a wrong answer pass deterministic checks as written?
3. Could a correct answer fail due to string-matching artifacts?
4. Are safety-critical endorsement checks sound (no false allow)?
5. Is the judge rubric aligned with deterministic checks?

## Output schema

For each scenario, emit:
- severity: low|medium|high
- issue_type: gameable_check|false_fail|rubric_mismatch|safety_gap|other
- evidence: short quote/snippet
- proposed_fix: concrete rule/rubric edit
