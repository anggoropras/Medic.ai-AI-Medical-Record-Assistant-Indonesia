from agents.validator import validate_record


def complete():
    return {
        "Patient Name": "Pasien Uji",
        "Age": 30,
        "Gender": "Laki-laki",
        "Chief Complaint": "Batuk",
        "Symptoms": "Batuk sejak dua hari",
        "Visit Date": "2026-09-12",
        "Diagnosis": None,
        "Treatment Plan": None,
        "Visit Type": "Kontrol",
    }


def test_complete_record_is_writable():
    result = validate_record(complete())
    assert result["status_data"] == "Lengkap"
    assert result["problem_fields"] == []


def test_missing_field_blocks_write():
    record = complete()
    record["Symptoms"] = None
    result = validate_record(record)
    assert result["status_data"] == "Data Tidak Lengkap"
    assert "Symptoms" in result["problem_fields"]


def test_invalid_age_blocks_write():
    record = complete()
    record["Age"] = 200
    result = validate_record(record)
    assert result["status_data"] == "Data Tidak Lengkap"
    assert "Age" in result["problem_fields"]


def test_invalid_date_blocks_write():
    record = complete()
    record["Visit Date"] = "12 September 2026"
    result = validate_record(record)
    assert result["status_data"] == "Data Tidak Lengkap"
    assert "Visit Date" in result["problem_fields"]
