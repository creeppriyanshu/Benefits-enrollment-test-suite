# Benefits Enrollment Test Suite (Health & Welfare Domain)

A mock **Health & Welfare (H&W) benefits enrollment API** + an Excel-driven
test suite that validates it — built to demonstrate H&W domain knowledge for
QA/testing roles (e.g. Wipro GET — H&W Tech).

This mirrors the same pattern as an API Test Runner: test cases live in
Excel, a Python script executes them against a REST API, and a pass/fail
HTML report gets generated automatically.

## What "Health & Welfare" testing covers

H&W is the employee-benefits domain used by benefits administration
platforms (bswift, PlanSource, Businessolver, Workday Benefits, etc.).
QA on this domain revolves around:

- **Eligibility rules** — is the employee active, past their waiting
  period, old enough to enroll?
- **Dependent eligibility** — spouse coverage, children aging out at 26
- **Open Enrollment window** — the one window per year employees can enroll
  without a special reason
- **Qualifying Life Events (QLE) / Special Enrollment Period (SEP)** —
  marriage, birth, divorce, death open a 30-day window to enroll outside
  the normal cycle
- **COBRA** — continuation coverage eligibility after termination

## Project structure

```
benefits_project/
├── app.py              # Mock H&W enrollment API (Flask)
├── build_test_cases.py # Generates test_cases.xlsx
├── test_cases.xlsx      # 18 test cases (input, expected, actual, pass/fail)
├── test_runner.py       # Executes test cases against the API, writes results
├── report.html          # Generated HTML pass/fail report
└── README.md
```

## API endpoints (app.py)

| Endpoint | Method | Purpose |
|---|---|---|
| `/eligibility/check` | POST | Check if an employee meets enrollment eligibility |
| `/dependents/<employee_id>` | GET | List dependents and their eligibility |
| `/enrollment/submit` | POST | Submit an enrollment (validates window / QLE) |
| `/life-event` | POST | Log a life event, returns the resulting SEP window |
| `/cobra/check` | POST | Check COBRA continuation eligibility after termination |

## How to run

```bash
pip install flask requests openpyxl jinja2

# Terminal 1 — start the mock API
python app.py

# Terminal 2 — run the test suite
python test_runner.py
```

This will:
1. Read all 18 test cases from `test_cases.xlsx`
2. Fire each request at the running API
3. Compare actual status code + response content against expected values
4. Write `Actual_Status`, `Actual_Response`, and `Result` (PASS/FAIL) back
   into `test_cases.xlsx`
5. Generate `report.html` — a summary dashboard with pass/fail counts and
   a per-test breakdown

## Sample test cases

| Test ID | Description |
|---|---|
| TC02 | Employee still in 30-day waiting period is rejected |
| TC07 | Child dependent aged 27 has aged out of eligibility |
| TC10 | Enrollment outside window without a QLE is rejected |
| TC11 | Enrollment outside window **with** a valid QLE is accepted |
| TC16 | COBRA eligible for terminated employee with prior enrollment |
| TC17 | COBRA not eligible — employer has fewer than 20 employees |

All 18 test cases pass against the reference implementation.
