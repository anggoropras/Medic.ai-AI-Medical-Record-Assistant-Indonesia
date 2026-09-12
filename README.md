# Medic.ai — AI Medical Record Assistant Indonesia

Production-oriented scaffold for a LangFlow medical-record assistant. It adds a WhatsApp adapter, patient-history memory interface, deterministic Medical Record ID generation, preview/confirmation state, and Extractor → Validator → Writer boundaries.

## Safety
Medic.ai is a documentation assistant, not a diagnostic or prescribing system. Never infer missing medical facts. Patient history is read-only context and must never auto-fill a new visit. Secrets and patient documents stay outside Git.

## Modules
- `whatsapp_webhook/` — WhatsApp Cloud API ↔ LangFlow adapter.
- `memory/` — vector-memory abstraction and patient history tool.
- `agents/` — extraction, validation and writing boundaries.
- `tools/` — deterministic Medical Record ID generation.
- `config/` — environment configuration.

## Run
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn whatsapp_webhook.main:app --reload --port 8000
```

Read `docs/ARCHITECTURE.md` and `docs/SECURITY.md` before connecting production patient data.
