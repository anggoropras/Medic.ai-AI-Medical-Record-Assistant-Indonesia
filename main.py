"""Medic.ai — AI Medical Record Assistant for Indonesia.

End-to-end pipeline:
WhatsApp/REST -> Extractor -> Validator -> Preview -> explicit confirmation -> Sheets -> Chroma memory.
The application never invents missing clinical facts and never writes without confirmation.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from agents.validator import validate_record
from memory.chroma_store import ChromaPatientHistory
from tools.generate_medical_record_id import generate_medical_record_id

load_dotenv()
TZ = ZoneInfo(os.getenv("TIMEZONE", "Asia/Jakarta"))
HEADERS = ["Medical Record ID", "Patient Name", "Age", "Gender", "Chief Complaint", "Symptoms", "Visit Date", "Diagnosis", "Treatment Plan", "Created Date", "Last Updated Date", "Visit Type"]

app = FastAPI(title="Medic.ai", version="2.0.0", description="AI Medical Record Assistant")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None
memory = ChromaPatientHistory(os.getenv("CHROMA_PERSIST_DIR", "./data/chroma"))
PENDING: dict[str, dict[str, Any]] = {}


def now() -> datetime:
    return datetime.now(TZ)


def normalize_gender(value: Any) -> Any:
    if value is None: return None
    s = str(value).strip().lower()
    return {"l": "Laki-laki", "lk": "Laki-laki", "male": "Laki-laki", "pria": "Laki-laki", "p": "Perempuan", "female": "Perempuan", "wanita": "Perempuan"}.get(s, value)


def normalize_date(value: Any) -> Any:
    if not value: return None
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try: return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError: pass
    return value


def parse_json(text: str) -> dict[str, Any]:
    text = text.strip().replace("```json", "").replace("```", "").strip()
    match = re.search(r"\{.*\}", text, re.S)
    if not match: raise ValueError("Extractor did not return JSON")
    data = json.loads(match.group(0))
    keys = ["Patient Name", "Age", "Gender", "Chief Complaint", "Symptoms", "Visit Date", "Diagnosis", "Treatment Plan", "Visit Type"]
    return {k: data.get(k) for k in keys}


async def extract(text: str) -> dict[str, Any]:
    if not client: raise RuntimeError("OPENAI_API_KEY belum dikonfigurasi")
    system = """Anda adalah Extractor Agent Medic.ai. Ekstrak HANYA fakta eksplisit dari pesan pengguna. Jangan mendiagnosis, menyimpulkan, menebak, atau memakai riwayat untuk mengisi data baru. Kembalikan JSON valid saja. Field: Patient Name, Age, Gender, Chief Complaint, Symptoms, Visit Date, Diagnosis, Treatment Plan, Visit Type. Field yang tidak disebutkan wajib null."""
    response = await client.chat.completions.create(model=os.getenv("OPENAI_MODEL", "gpt-4o"), temperature=0, response_format={"type": "json_object"}, messages=[{"role": "system", "content": system}, {"role": "user", "content": text}])
    return parse_json(response.choices[0].message.content or "{}")


def standardize(record: dict[str, Any]) -> dict[str, Any]:
    record = dict(record)
    record["Gender"] = normalize_gender(record.get("Gender"))
    record["Visit Date"] = normalize_date(record.get("Visit Date"))
    if record.get("Visit Type"): record["Visit Type"] = str(record["Visit Type"]).strip().title()
    return validate_record(record)


def preview(record: dict[str, Any]) -> str:
    labels = ["Patient Name", "Age", "Gender", "Chief Complaint", "Symptoms", "Visit Date", "Diagnosis", "Treatment Plan", "Visit Type"]
    lines = ["📋 *PREVIEW REKAM MEDIS*", ""]
    for key in labels: lines.append(f"• {key}: {record.get(key) if record.get(key) not in (None, '') else '—'}")
    lines += ["", "Apakah data ini sudah benar dan siap disimpan? *YA/TIDAK*"]
    return "\n".join(lines)


def _sheet():
    import gspread
    from google.oauth2.service_account import Credentials
    creds = Credentials.from_service_account_file(os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service-account.json"), scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return gspread.authorize(creds).open_by_key(os.environ["GOOGLE_SHEETS_ID"]).worksheet(os.getenv("GOOGLE_SHEETS_SHEET_NAME", "Sheet1"))


def ensure_headers(ws):
    current = ws.row_values(1)
    if current != HEADERS:
        if current: raise RuntimeError("Struktur kolom Google Sheets tidak sesuai schema A-L; tidak diubah otomatis.")
        ws.update("A1:L1", [HEADERS])


def save_record(record: dict[str, Any]) -> dict[str, Any]:
    ws = _sheet(); ensure_headers(ws)
    rows = ws.get_all_values()[1:]
    existing_ids = [r[0] for r in rows if r]
    record_id = generate_medical_record_id(now().date(), existing_ids)
    while record_id in existing_ids:
        n = int(record_id.rsplit("-", 1)[1]) + 1
        record_id = f"MR-{now():%Y%m%d}-{n:03d}"
    record = dict(record); record["Medical Record ID"] = record_id; record["Created Date"] = now().isoformat(); record["Last Updated Date"] = now().isoformat()
    ws.append_row([record.get(h, "") or "" for h in HEADERS], value_input_option="USER_ENTERED")
    try: memory.upsert(record)
    except Exception: pass
    return record


async def process(session_id: str, text: str, confirm: bool = False) -> dict[str, Any]:
    if confirm:
        pending = PENDING.pop(session_id, None)
        if not pending: return {"status": "no_pending", "message": "Tidak ada data yang menunggu konfirmasi."}
        record = save_record(pending)
        return {"status": "saved", "record": record, "message": f"✅ Rekam medis {record['Medical Record ID']} berhasil disimpan."}
    extracted = standardize(await extract(text))
    if extracted["status_data"] != "Lengkap":
        return {"status": "incomplete", "message": "Data belum lengkap. Mohon lengkapi: " + ", ".join(extracted["problem_fields"]), "record": extracted}
    history = []
    if extracted.get("Patient Name"):
        try: history = memory.search(patient_name=str(extracted["Patient Name"]), n_results=5)
        except Exception: history = []
    PENDING[session_id] = {k: extracted.get(k) for k in ["Patient Name", "Age", "Gender", "Chief Complaint", "Symptoms", "Visit Date", "Diagnosis", "Treatment Plan", "Visit Type"]}
    history_text = ""
    if history: history_text = "\n\n📚 *Riwayat pasien (read-only):*\n" + "\n".join(f"• {x['document']}" for x in history[:5])
    return {"status": "preview", "message": preview(extracted) + history_text, "record": extracted}


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str = "web"
    confirm: bool = False


@app.get("/health")
async def health(): return {"status": "ok", "service": "medic.ai", "version": "2.0.0"}


@app.post("/chat")
async def chat(req: ChatRequest):
    try: return await process(req.session_id, req.message, req.confirm)
    except Exception as exc: raise HTTPException(status_code=500, detail=str(exc)) from exc


def authorized(sender: str) -> bool:
    allowed = {x.strip() for x in os.getenv("AUTHORIZED_PHONE_NUMBERS", "").split(",") if x.strip()}
    return not allowed or sender in allowed


def valid_signature(raw: bytes, signature: str | None) -> bool:
    secret = os.getenv("WHATSAPP_APP_SECRET")
    if not secret: return True
    if not signature or not signature.startswith("sha256="): return False
    expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature[7:], expected)


async def send_whatsapp(to: str, text: str):
    token, phone_id = os.getenv("WHATSAPP_BUSINESS_TOKEN"), os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    if not token or not phone_id: raise RuntimeError("WhatsApp credentials belum dikonfigurasi")
    version = os.getenv("WHATSAPP_API_VERSION", "v23.0")
    async with httpx.AsyncClient(timeout=20) as http:
        r = await http.post(f"https://graph.facebook.com/{version}/{phone_id}/messages", headers={"Authorization": f"Bearer {token}"}, json={"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}})
        r.raise_for_status()


@app.get("/webhook/whatsapp")
async def whatsapp_verify(request: Request):
    q = request.query_params
    if q.get("hub.mode") == "subscribe" and q.get("hub.verify_token") == os.getenv("WHATSAPP_VERIFY_TOKEN"): return PlainTextResponse(q.get("hub.challenge", ""))
    raise HTTPException(status_code=403, detail="Webhook verification failed")


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    raw = await request.body()
    if not valid_signature(raw, request.headers.get("x-hub-signature-256")): raise HTTPException(status_code=401, detail="Invalid webhook signature")
    body = json.loads(raw or b"{}")
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            for msg in change.get("value", {}).get("messages", []):
                sender, text = msg.get("from"), msg.get("text", {}).get("body", "")
                if not sender or not text: continue
                if not authorized(sender):
                    await send_whatsapp(sender, "Nomor ini belum terdaftar sebagai pengguna Medic.ai yang berwenang."); continue
                sid, upper = f"wa:{sender}", text.strip().upper()
                if upper in {"TIDAK", "NO", "N", "BATAL", "CANCEL"}:
                    PENDING.pop(sid, None); reply = "❌ Rekam medis dibatalkan. Silakan kirim ulang data pasien."
                else:
                    result = await process(sid, "" if upper in {"YA", "YES", "Y"} else text, upper in {"YA", "YES", "Y"})
                    reply = result.get("message", "Terjadi kesalahan.")
                await send_whatsapp(sender, reply)
    return {"ok": True}


@app.get("/records")
async def records(limit: int = 50):
    ws = _sheet(); ensure_headers(ws); rows = ws.get_all_values()
    return {"total": max(0, len(rows) - 1), "records": [dict(zip(HEADERS, r)) for r in rows[1:limit + 1]]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=os.getenv("APP_HOST", "0.0.0.0"), port=int(os.getenv("APP_PORT", "8000")))
