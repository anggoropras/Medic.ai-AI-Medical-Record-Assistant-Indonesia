from datetime import date
from tools.generate_medical_record_id import generate_medical_record_id

def test_id_increments_per_day():
    d = date(2026, 9, 12)
    existing = ["MR-20260912-001", "MR-20260912-002", "MR-20260911-009"]
    assert generate_medical_record_id(d, existing) == "MR-20260912-003"
