from .vector_store import PatientHistoryStore

def sync_after_sheet_write(store: PatientHistoryStore, record: dict) -> None:
    store.upsert({
        "Medical Record ID": record.get("Medical Record ID"),
        "Patient Name": record.get("Patient Name"),
        "Chief Complaint": record.get("Chief Complaint"),
        "Diagnosis": record.get("Diagnosis"),
        "Treatment Plan": record.get("Treatment Plan"),
        "Visit Date": record.get("Visit Date"),
    })
