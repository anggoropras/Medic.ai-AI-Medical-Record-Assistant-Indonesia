REQUIRED = ["Patient Name", "Age", "Gender", "Chief Complaint", "Symptoms", "Visit Date"]

def validate_record(record: dict) -> dict:
    missing = [field for field in REQUIRED if record.get(field) in (None, "")]
    return {**record, "status_data": "Lengkap" if not missing else "Data Tidak Lengkap", "problem_fields": missing}
