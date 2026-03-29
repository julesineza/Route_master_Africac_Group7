# Acceptance Testing Report

| Requirement                                      | Steps                                                    | Expected                                                                | Actual                                                                          | Pass/Fail | Tester           | Date       |
| ------------------------------------------------ | -------------------------------------------------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------- | --------- | ---------------- | ---------- |
| Trader can register/login                        | Execute authentication and route protection tests        | Trader authentication helpers and access control behave correctly       | `tests/test_authentication.py`: 10/10 passed                                    | PASS      | Automated pytest | 2026-03-29 |
| Carrier can create and manage container workflow | Execute carrier unit tests and Flask functional suite    | Carrier container creation, listing, and detail logic operate correctly | `tests/test_carrier.py`: 14/14 passed, `tests/test_flask_app.py`: 26/26 passed  | PASS      | Automated pytest | 2026-03-29 |
| Trader can search and book container             | Execute trader unit tests and integration workflow tests | Trader route search and booking workflow complete successfully          | `tests/test_trader.py`: 13/13 passed, `tests/test_integration.py`: 13/13 passed | PASS      | Automated pytest | 2026-03-29 |
| Validation rules are enforced                    | Execute validation-focused subset                        | Invalid data is rejected and validations are applied consistently       | Validation run: 13 passed, 72 deselected                                        | PASS      | Automated pytest | 2026-03-29 |

## Summary

- Total acceptance scenarios: 4
- Passed: 4
- Failed: 0
- Acceptance result: ACCEPTED (automated acceptance criteria met)

## Evidence

- Unit testing output: `test_results/unit.txt` and `test_results/unit.xml` (46 passed)
- Validation testing output: `test_results/validation.txt` and `test_results/validation.xml` (13 passed)
- Integration testing output: `test_results/integration.txt` and `test_results/integration.xml` (13 passed)
- Functional/system testing output: `test_results/functional.txt` and `test_results/functional.xml` (26 passed)

## Sign-off

- Prepared by: Group 7 Route masterQA (Automated Test Execution)
- Date: 2026-03-29
