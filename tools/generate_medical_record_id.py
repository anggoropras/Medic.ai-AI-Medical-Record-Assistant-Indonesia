from datetime import date

def generate_medical_record_id(created_date: date, existing_ids: list[str]) -> str:
    prefix = f"MR-{created_date:%Y%m%d}-"
    numbers = []
    for value in existing_ids:
        if value.startswith(prefix):
            try: numbers.append(int(value.rsplit("-", 1)[1]))
            except ValueError: pass
    return f"{prefix}{max(numbers, default=0) + 1:03d}"
