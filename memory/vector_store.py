from typing import Protocol

class PatientHistoryStore(Protocol):
    def upsert(self, record: dict) -> None: ...
    def search(self, patient_name: str | None = None, medical_record_id: str | None = None) -> list[dict]: ...

class InMemoryHistoryStore:
    def __init__(self): self.records: list[dict] = []
    def upsert(self, record: dict) -> None: self.records.append(dict(record))
    def search(self, patient_name=None, medical_record_id=None):
        result = self.records
        if medical_record_id:
            result = [r for r in result if r.get("Medical Record ID") == medical_record_id]
        elif patient_name:
            needle = patient_name.strip().casefold()
            result = [r for r in result if str(r.get("Patient Name", "")).casefold() == needle]
        return result
