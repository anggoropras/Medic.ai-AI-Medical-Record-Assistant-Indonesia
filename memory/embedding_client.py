import os
from openai import OpenAI

def embed(text: str) -> list[float]:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    return client.embeddings.create(model=model, input=text).data[0].embedding

def visit_summary(record: dict) -> str:
    keys = ["Patient Name", "Chief Complaint", "Symptoms", "Diagnosis", "Treatment Plan", "Visit Date"]
    return " | ".join(f"{k}: {record.get(k)}" for k in keys if record.get(k) not in (None, ""))
