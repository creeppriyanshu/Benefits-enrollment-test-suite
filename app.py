"""
Mock Health & Welfare (HW) Benefits Enrollment API
----------------------------------------------------
Simulates a simplified employee benefits administration system —
the kind of platform tested on Wipro's H&W Tech account
(bswift / PlanSource / Businessolver-style enrollment systems).

Covers:
  - Employee eligibility (waiting period, employment status, age)
  - Dependent eligibility (spouse, child age-out at 26)
  - Open enrollment window vs. Qualifying Life Event (QLE) enrollment
  - Life events -> Special Enrollment Period (SEP)
  - COBRA continuation eligibility after termination

Run with:  python app.py
Serves on: http://127.0.0.1:5000
"""

from flask import Flask, request, jsonify
from datetime import datetime, timedelta

app = Flask(__name__)

# ---------------------------------------------------------------------------
# In-memory mock data (stands in for a real HRIS / benefits admin database)
# ---------------------------------------------------------------------------

EMPLOYEES = {
    "E001": {"name": "Amit Rao",     "age": 35, "employment_status": "Active",     "tenure_days": 400, "employer_size": 50, "enrolled_in_plan": True,  "termination_date": None},
    "E002": {"name": "Sana Gill",    "age": 22, "employment_status": "Active",     "tenure_days": 10,  "employer_size": 50, "enrolled_in_plan": False, "termination_date": None},
    "E003": {"name": "Rakesh Verma", "age": 45, "employment_status": "Terminated", "tenure_days": 900, "employer_size": 50, "enrolled_in_plan": True,  "termination_date": "2026-05-15"},
    "E004": {"name": "Neha Kapoor",  "age": 29, "employment_status": "Active",     "tenure_days": 250, "employer_size": 15, "enrolled_in_plan": True,  "termination_date": None},
}

DEPENDENTS = {
    "E001": [
        {"name": "Riya Rao",  "relation": "Spouse", "age": 33},
        {"name": "Aryan Rao", "relation": "Child",  "age": 8},
    ],
    "E004": [
        {"name": "Kabir Kapoor", "relation": "Child", "age": 27},  # aged out
    ],
}

VALID_EVENT_TYPES = {"marriage", "birth", "divorce", "death"}

OPEN_ENROLLMENT_WINDOW = {"start_month": 11, "start_day": 1, "end_month": 11, "end_day": 15}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_date(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d")


def is_within_open_enrollment(enrollment_date):
    d = parse_date(enrollment_date)
    start = datetime(d.year, OPEN_ENROLLMENT_WINDOW["start_month"], OPEN_ENROLLMENT_WINDOW["start_day"])
    end = datetime(d.year, OPEN_ENROLLMENT_WINDOW["end_month"], OPEN_ENROLLMENT_WINDOW["end_day"])
    return start <= d <= end


def check_employee_eligibility(emp):
    if emp["employment_status"] != "Active":
        return False, "Employee is not in Active employment status"
    if emp["tenure_days"] < 30:
        return False, "Employee has not completed the 30-day waiting period"
    if emp["age"] < 18:
        return False, "Employee does not meet minimum age requirement"
    return True, "Employee meets all eligibility criteria"


def check_dependent_eligibility(dep):
    if dep["relation"] == "Spouse":
        return True, "Spouse is eligible"
    if dep["relation"] == "Child":
        if dep["age"] < 26:
            return True, "Child is eligible (under age 26)"
        return False, "Child has aged out of eligibility (26 or older)"
    return False, "Unrecognized dependent relation type"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/eligibility/check", methods=["POST"])
def eligibility_check():
    data = request.get_json(silent=True) or {}
    employee_id = data.get("employee_id")
    emp = EMPLOYEES.get(employee_id)
    if not emp:
        return jsonify({"error": "Employee not found"}), 404

    eligible, reason = check_employee_eligibility(emp)
    return jsonify({"employee_id": employee_id, "eligible": eligible, "reason": reason}), 200


@app.route("/dependents/<employee_id>", methods=["GET"])
def get_dependents(employee_id):
    if employee_id not in EMPLOYEES:
        return jsonify({"error": "Employee not found"}), 404

    deps = DEPENDENTS.get(employee_id, [])
    result = []
    for dep in deps:
        eligible, reason = check_dependent_eligibility(dep)
        result.append({**dep, "eligible": eligible, "reason": reason})

    return jsonify({"employee_id": employee_id, "dependents": result}), 200


@app.route("/enrollment/submit", methods=["POST"])
def submit_enrollment():
    data = request.get_json(silent=True) or {}
    employee_id = data.get("employee_id")
    plan_id = data.get("plan_id")
    enrollment_date = data.get("enrollment_date")
    is_qle = data.get("is_qle", False)

    emp = EMPLOYEES.get(employee_id)
    if not emp:
        return jsonify({"error": "Employee not found"}), 404
    if not plan_id or not enrollment_date:
        return jsonify({"error": "plan_id and enrollment_date are required"}), 400

    eligible, reason = check_employee_eligibility(emp)
    if not eligible:
        return jsonify({"status": "Rejected", "reason": reason}), 200

    if not is_within_open_enrollment(enrollment_date) and not is_qle:
        return jsonify({
            "status": "Rejected",
            "reason": "Enrollment date falls outside the open enrollment window and no qualifying life event was provided"
        }), 200

    return jsonify({
        "status": "Enrolled",
        "employee_id": employee_id,
        "plan_id": plan_id,
        "reason": "Enrollment accepted"
    }), 200


@app.route("/life-event", methods=["POST"])
def life_event():
    data = request.get_json(silent=True) or {}
    employee_id = data.get("employee_id")
    event_type = data.get("event_type")
    event_date = data.get("event_date")

    if employee_id not in EMPLOYEES:
        return jsonify({"error": "Employee not found"}), 404
    if event_type not in VALID_EVENT_TYPES:
        return jsonify({"error": f"Invalid event_type. Must be one of {sorted(VALID_EVENT_TYPES)}"}), 400
    if not event_date:
        return jsonify({"error": "event_date is required"}), 400

    start = parse_date(event_date)
    end = start + timedelta(days=30)

    return jsonify({
        "employee_id": employee_id,
        "event_type": event_type,
        "sep_start": start.strftime("%Y-%m-%d"),
        "sep_end": end.strftime("%Y-%m-%d"),
        "valid": True
    }), 200


@app.route("/cobra/check", methods=["POST"])
def cobra_check():
    data = request.get_json(silent=True) or {}
    employee_id = data.get("employee_id")
    termination_date = data.get("termination_date")

    emp = EMPLOYEES.get(employee_id)
    if not emp:
        return jsonify({"error": "Employee not found"}), 404
    if not termination_date:
        return jsonify({"error": "termination_date is required"}), 400

    if not emp["enrolled_in_plan"]:
        return jsonify({"eligible": False, "reason": "Employee was not enrolled in a plan at termination"}), 200
    if emp["employer_size"] < 20:
        return jsonify({"eligible": False, "reason": "Employer has fewer than 20 employees; not subject to COBRA"}), 200

    term = parse_date(termination_date)
    coverage_end = term + timedelta(days=548)  # ~18 months

    return jsonify({
        "eligible": True,
        "employee_id": employee_id,
        "coverage_end_date": coverage_end.strftime("%Y-%m-%d"),
        "reason": "Eligible for COBRA continuation coverage for 18 months"
    }), 200


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
