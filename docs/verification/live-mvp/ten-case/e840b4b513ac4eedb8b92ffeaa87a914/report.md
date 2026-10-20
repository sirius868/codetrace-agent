# CodeTrace evaluation

Mode: **live**; status: completed; live: run

Offline responses are scripted; citation validity is not semantic accuracy.

Report: `e840b4b513ac4eedb8b92ffeaa87a914`; dataset: `d8d814a583c28439bdb9cb0c167fcfdee2e17d8f11eb354ad817452aff371a81`

| Case | Status | File coverage | Citation validity | Human semantic correct |
| --- | --- | --- | --- | --- |
| python-entry | completed | 1.0 | 1.0 | None |
| python-cross-file | completed | 1.0 | 1.0 | None |
| python-config | completed | 1.0 | 1.0 | None |
| python-exception | completed | 1.0 | 1.0 | None |
| python-no-answer | insufficient_evidence | None | None | None |
| java-entry | completed | 1.0 | 1.0 | None |
| java-cross-file | completed | 1.0 | 1.0 | None |
| java-config | completed | 1.0 | 1.0 | None |
| java-exception | completed | 1.0 | 1.0 | None |
| java-no-answer | insufficient_evidence | None | None | None |

Summary (null = unknown / no denominator):

```json
{
  "total": 10,
  "measured": 10,
  "case_errors": 0,
  "statuses": {
    "completed": 8,
    "insufficient_evidence": 2
  },
  "file_coverage": {
    "numerator": 14,
    "denominator": 14,
    "value": 1.0
  },
  "citation_validity": {
    "numerator": 43,
    "denominator": 43,
    "value": 1.0
  },
  "usage_known_cases": 10,
  "reviewed": 0,
  "semantic_review": {
    "numerator": 0,
    "denominator": 0,
    "value": null
  },
  "live_success_rate": null
}
```
