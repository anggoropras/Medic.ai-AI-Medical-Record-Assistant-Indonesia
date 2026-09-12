import os
import chromadb
from .embedding_client import embed, visit_summary

class ChromaPatientHistory:
    def __init__(self, path: str = "./vector_db"):
        self.client = chromadb.PersistentClient(path=path)
        self.collection = self.client.get_or_create_collection("patient_history")

    def upsert(self, record: dict) -> None:
        record_id = str(record.get("Medical Record ID"))
        if not record_id or record_id == "None":
            raise ValueError("Medical Record ID is required")
        self.collection.upsert(
            ids=[record_id],
            embeddings=[embed(visit_summary(record))],
            documents=[visit_summary(record)],
            metadatas=[{
                "medical_record_id": record_id,
                "patient_name": str(record.get("Patient Name", "")),
                "visit_date": str(record.get("Visit Date", "")),
            }],
        )

    def search(self, patient_name=None, medical_record_id=None, n_results: int = 5) -> list[dict]:
        where = None
        if medical_record_id:
            where = {"medical_record_id": medical_record_id}
        elif patient_name:
            where = {"patient_name": patient_name}
        result = self.collection.query(query_embeddings=[embed(patient_name or medical_record_id or "")], n_results=n_results, where=where)
        return [{"document": doc, "metadata": meta} for doc, meta in zip(result.get("documents", [[]])[0], result.get("metadatas", [[]])[0])]
