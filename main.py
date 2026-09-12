"""
FastAPI application — REST + WhatsApp webhook entrypoint.

Endpoints:
  POST /chat          — REST API (Playground / web UI)
  POST /webhook/whatsapp — Twilio inbound webhook
  GET  /health        — Health check
  GET  /records       — List all records (paginated)
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from loguru import logger
from openai import AsyncOpenAI
from pydantic import BaseModel

from src.agents.extractor import ExtractorAgent
from src.agents.validator import ValidatorAgent
from src.agents.writer import WriterAgent
from src.models.medical_record import ExtractedRecord, MedicalRecord
from src.orchestrator import MedicalRecordOrchestrator
from src.services.memory import MemoryService
from src.services.record_id import RecordIDService
from src.services.sheets import SheetsService
from src.services.whatsapp import WhatsAppService

load_dotenv()

# ── In-memory pending sessions (keyed by sender phone number) ─────────────────
# In production, replace with Redis or a persistent store.
_PENDING: dict[str, ExtractedRecord] = {}

# ── Shared service instances ──────────────────────────────────────────────────
_orchestrator: Optional[MedicalRecordOrchestrator] = None
_whatsapp: Optional[WhatsAppService] = None


def _build_orchestrator() -> MedicalRecordOrchestrator:
    openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    sheets = SheetsService(
        spreadsheet_id=os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", ""),
        sheet_name=os.getenv("GOOGLE_SHEETS_SHEET_NAME", "Sheet1"),
        service_account_file=os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE"),
    )

    record_id_svc = RecordIDService(sheets)
    memory = MemoryService(persist_dir=os.getenv("CHROMA_PERSIST_DIR", "./data/chroma"))

    extractor = ExtractorAgent(client=openai_client, model="gpt-4o")
    validator = ValidatorAgent()
    writer = WriterAgent(sheets=sheets, record_id=record_id_svc)

    return MedicalRecordOrchestrator(
        extractor=extractor,
        validator=validator,
        writer=writer,
        memory=memory,
        timezone=os.getenv("TIMEZONE", "Asia/Jakarta"),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _orchestrator, _whatsapp

    logger.info("Starting Rekam Medis AI...")
    _orchestrator = _build_orchestrator()
    _whatsapp = WhatsAppService()

    # Ensure Sheets has header row
    from src.models.medical_record import MedicalRecord as MR
    await _orchestrator.writer.sheets.ensure_headers(MR.sheets_headers())

    logger.info("✅ Rekam Medis AI ready")
    yield
    logger.info("Shutting down...")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Rekam Medis AI",
    version="1.0.0",
    description="AI Medical Record Assistant — Extract, Validate, Store",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── REST: Chat endpoint ───────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    confirm: bool = False


class ChatResponse(BaseModel):
    success: bool
    status: str
    message: str
    record_id: Optional[str] = None
    preview: Optional[str] = None


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    REST endpoint for web/playground interaction.

    - Send message → get preview
    - Send confirm=true with same session_id → save record
    """
    if _orchestrator is None:
        raise HTTPException(status_code=503, detail="Service not ready")

    pending = _PENDING.get(req.session_id) if req.session_id else None

    result = await _orchestrator.process(
        user_input=req.message,
        confirm=req.confirm,
        pending_extracted=pending if req.confirm else None,
    )

    # Store pending extraction for confirmation flow
    if result.message == "preview" and req.session_id and result.extracted:
        _PENDING[req.session_id] = result.extracted
    elif req.session_id and req.session_id in _PENDING:
        del _PENDING[req.session_id]

    return ChatResponse(
        success=result.success,
        status=result.status.value,
        message=result.message if result.message != "preview" else result.preview or "",
        record_id=result.record.medical_record_id if result.record else None,
        preview=result.preview,
    )


# ── WhatsApp Webhook ──────────────────────────────────────────────────────────

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """
    Twilio inbound WhatsApp webhook.

    Flow:
    1. User sends patient info → system replies with preview
    2. User replies YA → record saved
    3. User replies TIDAK → cancelled
    """
    if _orchestrator is None or _whatsapp is None:
        return PlainTextResponse("Service not ready", status_code=503)

    form = await request.form()
    inbound = WhatsAppService.parse_inbound(dict(form))
    sender = inbound["from"]
    body = inbound["body"]

    logger.info(f"[WhatsApp] From {sender}: {body[:80]}")

    # ── Handle confirmation ────────────────────────────────────────────────
    if body.upper() in ("YA", "YES", "Y") and sender in _PENDING:
        result = await _orchestrator.process(
            user_input="",
            confirm=True,
            pending_extracted=_PENDING.pop(sender),
        )
        if result.success and result.record:
            _whatsapp.send_confirmation(sender, result.record)
        else:
            _whatsapp.send(sender, result.message)
        return PlainTextResponse("OK")

    if body.upper() in ("TIDAK", "NO", "N", "CANCEL", "BATAL"):
        _PENDING.pop(sender, None)
        _whatsapp.send(sender, "❌ Rekam medis dibatalkan. Silakan kirim ulang data pasien.")
        return PlainTextResponse("OK")

    # ── New input ──────────────────────────────────────────────────────────
    result = await _orchestrator.process(user_input=body, confirm=False)

    if result.message == "preview" and result.extracted:
        _PENDING[sender] = result.extracted
        _whatsapp.send(sender, result.preview or "")

    elif not result.success and result.validation:
        if result.validation.missing_fields:
            _whatsapp.send_missing_fields(sender, result.validation.missing_fields)
        else:
            _whatsapp.send(sender, result.message)

    else:
        _whatsapp.send(sender, result.message)

    return PlainTextResponse("OK")


# ── Records endpoint ──────────────────────────────────────────────────────────

@app.get("/records")
async def list_records(limit: int = 50, offset: int = 0):
    """Return all medical records from Sheets (paginated)."""
    if _orchestrator is None:
        raise HTTPException(status_code=503, detail="Service not ready")

    rows = await _orchestrator.writer.sheets.get_all_rows()
    headers = MedicalRecord.sheets_headers()
    paginated = rows[offset: offset + limit]

    records = [dict(zip(headers, row)) for row in paginated]
    return {"total": len(rows), "offset": offset, "limit": limit, "records": records}


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "rekam-medis-ai", "version": "1.0.0"}


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", "8000")),
        reload=False,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
