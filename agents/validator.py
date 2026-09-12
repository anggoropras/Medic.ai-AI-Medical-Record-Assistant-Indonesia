"""Deterministic validation layer for Medic.ai.

Validation never invents clinical data. It only normalizes safe formats and checks
required fields/ambiguity before the Writer is allowed to persist anything.
"""
from datetime import datetime

REQUIRED = ["Patient Name", "Age", "Gender", "Chief Complaint", "Symptoms", "Visit Date"]
ALLOWED_GENDER = {"Laki-laki", "Perempuan"}


def _date_ok(value: object) -> bool:
    if not value:
        return False
    try:
        datetime.strptime(str(value), "%Y-%m-%d")
        return True
    except ValueError:
        return False


def validate_record(record: dict) -> dict:
    record = dict(record)
    missing = [field for field in REQUIRED if record.get(field) in (None, "")]
    problems = list(missing)

    if record.get("Age") not in (None, ""):
        try:
            age = int(record["Age"])
            if not 0 <= age <= 130:
                problems.append("Age")
            else:
                record["Age"] = age
        except (TypeError, ValueError):
            problems.append("Age")

    if record.get("Gender") not in (None, "") and record["Gender"] not in ALLOWED_GENDER:
        problems.append("Gender")

    if record.get("Visit Date") not in (None, "") and not _date_ok(record["Visit Date"]):
        problems.append("Visit Date")

    # Preserve order while removing duplicates.
    problems = list(dict.fromkeys(problems))
    return {
        **record,
        "status_data": "Lengkap" if not problems else "Data Tidak Lengkap",
        "problem_fields": problems,
    }
