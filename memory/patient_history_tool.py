from .vector_store import PatientHistoryStore

class PatientHistoryTool:
    name = "patient_history_lookup"
    description = "Read-only lookup of previous patient visits. Never use results to auto-fill a new visit."
    def __init__(self, store: PatientHistoryStore): self.store = store
    def lookup(self, patient_name=None, medical_record_id=None):
        return self.store.search(patient_name=patient_name, medical_record_id=medical_record_id)
