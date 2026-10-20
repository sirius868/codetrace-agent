# CodeTrace 成对评测 v2

模式: live; report_id: b6eb60d1425c4bf1bc1aed55dccc3740

离线只验证控制链路。人工未确认保持未知。两模式是整体方案比较，不是BM25因果实验。费用未知。

| Case | Variant | Status | Attempts | Human semantic success |
|---|---|---|---|---|
| petclinic-entry | literal | context_budget | 1 | None |
| petclinic-entry | indexed | completed | 1 | None |
| petclinic-owner-search | literal | completed | 1 | None |
| petclinic-owner-search | indexed | completed | 1 | None |
| petclinic-visit | literal | invalid_answer | 1 | None |
| petclinic-visit | indexed | invalid_answer | 1 | None |
| petclinic-config | literal | completed | 1 | None |
| petclinic-config | indexed | completed | 1 | None |
| petclinic-owner-missing | literal | completed | 1 | None |
| petclinic-owner-missing | indexed | completed | 1 | None |
| petclinic-pet-validator | literal | completed | 1 | None |
| petclinic-pet-validator | indexed | invalid_answer | 1 | None |
| petclinic-runtime-db | literal | max_tools | 1 | None |
| petclinic-runtime-db | indexed | max_tools | 1 | None |
| petclinic-runtime-overload | literal | completed | 1 | None |
| petclinic-runtime-overload | indexed | invalid_answer | 1 | None |
| flask-entry | literal | completed | 1 | None |
| flask-entry | indexed | max_rounds | 1 | None |
| flask-session-open | literal | max_rounds | 1 | None |
| flask-session-open | indexed | context_budget | 1 | None |
| flask-test-session | literal | max_rounds | 1 | None |
| flask-test-session | indexed | completed | 1 | None |
| flask-propagate | literal | completed | 1 | None |
| flask-propagate | indexed | completed | 1 | None |
| flask-user-exception | literal | max_rounds | 1 | None |
| flask-user-exception | indexed | completed | 1 | None |
| flask-invalid-cookie | literal | completed | 1 | None |
| flask-invalid-cookie | indexed | completed | 1 | None |
| flask-runtime-key | literal | model_error | 1 | None |
| flask-runtime-key | indexed | model_error | 1 | None |
| flask-runtime-session | literal | model_error | 1 | None |
| flask-runtime-session | indexed | model_error | 1 | None |
| mall-entry | literal | not_run | 0 | None |
| mall-entry | indexed | not_run | 0 | None |
| mall-login | literal | not_run | 0 | None |
| mall-login | indexed | not_run | 0 | None |
| mall-password-error | literal | not_run | 0 | None |
| mall-password-error | indexed | not_run | 0 | None |
| mall-expiration | literal | not_run | 0 | None |
| mall-expiration | indexed | not_run | 0 | None |
| mall-validation-error | literal | not_run | 0 | None |
| mall-validation-error | indexed | not_run | 0 | None |
| mall-auth-error | literal | not_run | 0 | None |
| mall-auth-error | indexed | not_run | 0 | None |
| mall-runtime-redis | literal | not_run | 0 | None |
| mall-runtime-redis | indexed | not_run | 0 | None |
| mall-runtime-token | literal | not_run | 0 | None |
| mall-runtime-token | indexed | not_run | 0 | None |

```json
{
  "planned": 48,
  "ran": 32,
  "reviewed": 0,
  "cost": null,
  "modes": {
    "literal": {
      "planned": 24,
      "ran": 16,
      "reviewed": 0,
      "successes": 0,
      "success_rate": null,
      "held_out_planned": 8,
      "held_out_successes": 0,
      "held_out_rate": null,
      "failures": 8,
      "not_run": 8,
      "elapsed_ms_median": 32212.915,
      "elapsed_ms_max": 99783.51
    },
    "indexed": {
      "planned": 24,
      "ran": 16,
      "reviewed": 0,
      "successes": 0,
      "success_rate": null,
      "held_out_planned": 8,
      "held_out_successes": 0,
      "held_out_rate": null,
      "failures": 8,
      "not_run": 8,
      "elapsed_ms_median": 38156.47,
      "elapsed_ms_max": 148997.9
    }
  },
  "pairs": [
    {
      "case_id": "petclinic-entry",
      "literal_success": null,
      "indexed_success": null,
      "indexed_minus_literal": {
        "file_group_coverage": 1.0,
        "evidence_group_coverage": 0.0,
        "elapsed_ms": 7282.320000000003,
        "model_attempts": 0,
        "tool_count": -2
      }
    },
    {
      "case_id": "petclinic-owner-search",
      "literal_success": null,
      "indexed_success": null,
      "indexed_minus_literal": {
        "file_group_coverage": 0.0,
        "evidence_group_coverage": 0.0,
        "elapsed_ms": 2313.6899999999987,
        "model_attempts": 1,
        "tool_count": -2
      }
    },
    {
      "case_id": "petclinic-visit",
      "literal_success": null,
      "indexed_success": null,
      "indexed_minus_literal": {
        "file_group_coverage": 0.0,
        "evidence_group_coverage": 0.0,
        "elapsed_ms": 49214.39,
        "model_attempts": 0,
        "tool_count": -3
      }
    },
    {
      "case_id": "petclinic-config",
      "literal_success": null,
      "indexed_success": null,
      "indexed_minus_literal": {
        "file_group_coverage": 0.0,
        "evidence_group_coverage": 0.0,
        "elapsed_ms": 4510.919999999998,
        "model_attempts": 0,
        "tool_count": 1
      }
    },
    {
      "case_id": "petclinic-owner-missing",
      "literal_success": null,
      "indexed_success": null,
      "indexed_minus_literal": {
        "file_group_coverage": 0.0,
        "evidence_group_coverage": 0.0,
        "elapsed_ms": 1270.630000000001,
        "model_attempts": 0,
        "tool_count": 0
      }
    },
    {
      "case_id": "petclinic-pet-validator",
      "literal_success": null,
      "indexed_success": null,
      "indexed_minus_literal": {
        "file_group_coverage": -1.0,
        "evidence_group_coverage": 0.0,
        "elapsed_ms": 32988.34,
        "model_attempts": 1,
        "tool_count": 1
      }
    },
    {
      "case_id": "petclinic-runtime-db",
      "literal_success": null,
      "indexed_success": null,
      "indexed_minus_literal": {
        "file_group_coverage": 0.0,
        "evidence_group_coverage": 0.0,
        "elapsed_ms": 1200.4400000000023,
        "model_attempts": 1,
        "tool_count": -1
      }
    },
    {
      "case_id": "petclinic-runtime-overload",
      "literal_success": null,
      "indexed_success": null,
      "indexed_minus_literal": {
        "file_group_coverage": -1.0,
        "evidence_group_coverage": 0.0,
        "elapsed_ms": 39700.24,
        "model_attempts": 0,
        "tool_count": -2
      }
    },
    {
      "case_id": "flask-entry",
      "literal_success": null,
      "indexed_success": null,
      "indexed_minus_literal": {
        "file_group_coverage": -1.0,
        "evidence_group_coverage": -1.0,
        "elapsed_ms": 15546.779999999999,
        "model_attempts": 3,
        "tool_count": 2
      }
    },
    {
      "case_id": "flask-session-open",
      "literal_success": null,
      "indexed_success": null,
      "indexed_minus_literal": {
        "file_group_coverage": 0.0,
        "evidence_group_coverage": 0.0,
        "elapsed_ms": -4719.919999999998,
        "model_attempts": -4,
        "tool_count": 1
      }
    },
    {
      "case_id": "flask-test-session",
      "literal_success": null,
      "indexed_success": null,
      "indexed_minus_literal": {
        "file_group_coverage": 1.0,
        "evidence_group_coverage": 0.3333333333333333,
        "elapsed_ms": 244.8199999999997,
        "model_attempts": -1,
        "tool_count": 0
      }
    },
    {
      "case_id": "flask-propagate",
      "literal_success": null,
      "indexed_success": null,
      "indexed_minus_literal": {
        "file_group_coverage": 0.0,
        "evidence_group_coverage": 0.0,
        "elapsed_ms": 5648.610000000001,
        "model_attempts": 1,
        "tool_count": 5
      }
    },
    {
      "case_id": "flask-user-exception",
      "literal_success": null,
      "indexed_success": null,
      "indexed_minus_literal": {
        "file_group_coverage": 1.0,
        "evidence_group_coverage": 0.0,
        "elapsed_ms": 8120.3299999999945,
        "model_attempts": 0,
        "tool_count": -2
      }
    },
    {
      "case_id": "flask-invalid-cookie",
      "literal_success": null,
      "indexed_success": null,
      "indexed_minus_literal": {
        "file_group_coverage": 0.0,
        "evidence_group_coverage": 0.0,
        "elapsed_ms": 7944.630000000001,
        "model_attempts": 1,
        "tool_count": 2
      }
    },
    {
      "case_id": "flask-runtime-key",
      "literal_success": null,
      "indexed_success": null,
      "indexed_minus_literal": {
        "file_group_coverage": 0.0,
        "evidence_group_coverage": 0.0,
        "elapsed_ms": -8901.28,
        "model_attempts": -1,
        "tool_count": -2
      }
    },
    {
      "case_id": "flask-runtime-session",
      "literal_success": null,
      "indexed_success": null,
      "indexed_minus_literal": {
        "file_group_coverage": 0.0,
        "evidence_group_coverage": 0.0,
        "elapsed_ms": -52.71000000000001,
        "model_attempts": 0,
        "tool_count": 0
      }
    },
    {
      "case_id": "mall-entry",
      "literal_success": null,
      "indexed_success": null,
      "indexed_minus_literal": {
        "file_group_coverage": null,
        "evidence_group_coverage": null,
        "elapsed_ms": null,
        "model_attempts": null,
        "tool_count": null
      }
    },
    {
      "case_id": "mall-login",
      "literal_success": null,
      "indexed_success": null,
      "indexed_minus_literal": {
        "file_group_coverage": null,
        "evidence_group_coverage": null,
        "elapsed_ms": null,
        "model_attempts": null,
        "tool_count": null
      }
    },
    {
      "case_id": "mall-password-error",
      "literal_success": null,
      "indexed_success": null,
      "indexed_minus_literal": {
        "file_group_coverage": null,
        "evidence_group_coverage": null,
        "elapsed_ms": null,
        "model_attempts": null,
        "tool_count": null
      }
    },
    {
      "case_id": "mall-expiration",
      "literal_success": null,
      "indexed_success": null,
      "indexed_minus_literal": {
        "file_group_coverage": null,
        "evidence_group_coverage": null,
        "elapsed_ms": null,
        "model_attempts": null,
        "tool_count": null
      }
    },
    {
      "case_id": "mall-validation-error",
      "literal_success": null,
      "indexed_success": null,
      "indexed_minus_literal": {
        "file_group_coverage": null,
        "evidence_group_coverage": null,
        "elapsed_ms": null,
        "model_attempts": null,
        "tool_count": null
      }
    },
    {
      "case_id": "mall-auth-error",
      "literal_success": null,
      "indexed_success": null,
      "indexed_minus_literal": {
        "file_group_coverage": null,
        "evidence_group_coverage": null,
        "elapsed_ms": null,
        "model_attempts": null,
        "tool_count": null
      }
    },
    {
      "case_id": "mall-runtime-redis",
      "literal_success": null,
      "indexed_success": null,
      "indexed_minus_literal": {
        "file_group_coverage": null,
        "evidence_group_coverage": null,
        "elapsed_ms": null,
        "model_attempts": null,
        "tool_count": null
      }
    },
    {
      "case_id": "mall-runtime-token",
      "literal_success": null,
      "indexed_success": null,
      "indexed_minus_literal": {
        "file_group_coverage": null,
        "evidence_group_coverage": null,
        "elapsed_ms": null,
        "model_attempts": null,
        "tool_count": null
      }
    }
  ],
  "analysis_ready_for_programming": false
}
```
