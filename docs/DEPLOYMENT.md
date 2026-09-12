# Medic.ai Deployment

## 1. Local setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `OPENAI_API_KEY`, `GOOGLE_SHEETS_ID`, `GOOGLE_SERVICE_ACCOUNT_FILE`, and the WhatsApp variables before starting.

## 2. Google Sheets

1. Create a Google Cloud service account.
2. Enable Google Sheets API.
3. Download the service-account JSON outside Git and set `GOOGLE_SERVICE_ACCOUNT_FILE`.
4. Share the target spreadsheet with the service account email as Editor.
5. Keep the existing A-L schema unchanged. Medic.ai refuses to overwrite a non-empty incompatible header row.

Columns A-L:
`Medical Record ID | Patient Name | Age | Gender | Chief Complaint | Symptoms | Visit Date | Diagnosis | Treatment Plan | Created Date | Last Updated Date | Visit Type`

## 3. Start API

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Health check: `GET /health`

REST flow:
- `POST /chat` with patient information -> preview
- repeat with the same `session_id` and `confirm: true` -> write to Sheets

No record is written without explicit confirmation.

## 4. WhatsApp Cloud API

Configure a Meta WhatsApp Business app with:
- Callback URL: `https://YOUR-DOMAIN/webhook/whatsapp`
- Verify token: same value as `WHATSAPP_VERIFY_TOKEN`
- App secret: `WHATSAPP_APP_SECRET`
- Access token: `WHATSAPP_BUSINESS_TOKEN`
- Phone number ID: `WHATSAPP_PHONE_NUMBER_ID`

The verification endpoint uses Meta's `hub.mode`, `hub.verify_token`, and `hub.challenge` parameters. Incoming webhook signatures are checked when `WHATSAPP_APP_SECRET` is configured.

Restrict production access with `AUTHORIZED_PHONE_NUMBERS` as a comma-separated allowlist.

## 5. Patient memory

After a successful Sheets write, Medic.ai attempts to store a visit summary in Chroma under `CHROMA_PERSIST_DIR`. Memory is read-only context: it must never fill new clinical fields automatically.

## 6. Security checklist

- Never commit `.env` or the Google service-account JSON.
- Use HTTPS for WhatsApp webhooks.
- Keep `AUTHORIZED_PHONE_NUMBERS` restricted.
- Rotate API credentials if exposed.
- Do not put real patient data in tests, screenshots, issues, or documentation.
- Medic.ai is an administrative documentation assistant, not a diagnostic or prescribing system.

## 7. Tests

```bash
pytest -q
```

Tests cover deterministic Medical Record ID generation, required-field validation, date/age validation, and the explicit Writer confirmation boundary.
