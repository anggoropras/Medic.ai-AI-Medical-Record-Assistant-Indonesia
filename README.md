# 🏥 Rekam Medis AI

AI-powered medical record assistant yang mengubah percakapan natural menjadi data rekam medis terstruktur di Google Sheets.

---

## 🏗️ Arsitektur

```
Chat / WhatsApp Input
        │
        ▼
┌─────────────────┐
│ ExtractorAgent  │  GPT-4o — ekstrak field dari teks natural
└────────┬────────┘
         │ ExtractedRecord + confidence scores
         ▼
┌─────────────────┐
│ ValidatorAgent  │  Rule-based — cek completeness, konsistensi, ambiguity
└────────┬────────┘
         │ ValidationResult
         ▼
┌─────────────────┐
│    Preview      │  Tampilkan data ke user, minta konfirmasi
└────────┬────────┘
         │ user: YA
         ▼
┌─────────────────┐
│  WriterAgent    │  Auto-generate MR-ID, append/update ke Google Sheets
└────────┬────────┘
         │ MedicalRecord
         ▼
┌─────────────────┐
│ MemoryService   │  Simpan ke ChromaDB untuk long-term patient memory
└────────┬────────┘
         │
         ▼
    Chat / WhatsApp Output (konfirmasi)
```

---

## 📁 Struktur Project

```
rekam-medis-ai/
├── main.py                      # FastAPI entrypoint
├── requirements.txt
├── .env.example
├── credentials/
│   └── service_account.json     # Google Service Account (jangan di-commit!)
├── data/
│   └── chroma/                  # ChromaDB persistent storage
└── src/
    ├── agents/
    │   ├── extractor.py         # Agent 1: Ekstraksi data medis
    │   ├── validator.py         # Agent 2: Validasi kelengkapan & konsistensi
    │   └── writer.py            # Agent 3: Tulis ke Google Sheets
    ├── models/
    │   └── medical_record.py    # Pydantic schemas
    ├── services/
    │   ├── sheets.py            # Google Sheets API v4
    │   ├── memory.py            # ChromaDB long-term memory
    │   ├── record_id.py         # Auto-generate MR-YYYYMMDD-NNN
    │   └── whatsapp.py          # Twilio WhatsApp messaging
    └── orchestrator.py          # Pipeline coordinator
```

---

## 🚀 Setup

### 1. Install dependencies
```bash
cd rekam-medis-ai
pip install -r requirements.txt
```

### 2. Konfigurasi environment
```bash
cp .env.example .env
# Edit .env dengan credentials Anda
```

### 3. Google Service Account
1. Buka [Google Cloud Console](https://console.cloud.google.com)
2. Buat Service Account → download JSON key
3. Simpan ke `credentials/service_account.json`
4. Share spreadsheet ke email service account (Editor access)

### 4. Jalankan server
```bash
python main.py
# atau dengan uvicorn:
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 📡 API Endpoints

### `POST /chat`
REST endpoint untuk web/playground.

```json
// Request
{
  "message": "Pasien baru Budi Santoso, laki-laki 35 tahun, demam dan batuk sejak 2 hari",
  "session_id": "session-abc123",
  "confirm": false
}

// Response (preview)
{
  "success": false,
  "status": "Memerlukan Konfirmasi",
  "message": "📋 Preview Rekam Medis...",
  "preview": "..."
}

// Confirm
{
  "message": "",
  "session_id": "session-abc123",
  "confirm": true
}

// Response (saved)
{
  "success": true,
  "status": "Lengkap",
  "message": "✅ Rekam medis berhasil disimpan!",
  "record_id": "MR-20260115-001"
}
```

### `POST /webhook/whatsapp`
Twilio inbound webhook. Configure di Twilio Console → Messaging → WhatsApp Sandbox.

```
Webhook URL: https://your-domain.com/webhook/whatsapp
```

**Flow WhatsApp:**
```
Dokter: "Pasien Budi Santoso, laki-laki 35thn, demam batuk 2 hari"
   Bot: "📋 Preview Rekam Medis ... Balas YA untuk menyimpan"
Dokter: "YA"
   Bot: "✅ Rekam medis MR-20260115-001 berhasil disimpan!"
```

### `GET /records?limit=50&offset=0`
Ambil semua rekam medis dari Sheets (paginated).

### `GET /health`
Health check.

---

## 🗂️ Google Sheets Schema

| Kolom | Field              |
|-------|--------------------|
| A     | Medical Record ID  |
| B     | Patient Name       |
| C     | Age                |
| D     | Gender             |
| E     | Visit Date         |
| F     | Chief Complaint    |
| G     | Symptoms           |
| H     | Diagnosis          |
| I     | Treatment Plan     |
| J     | Doctor Notes       |
| K     | Created Date       |
| L     | Last Updated Date  |

---

## 🆔 Format Medical Record ID

```
MR-YYYYMMDD-NNN

Contoh:
MR-20260115-001  → Rekam medis ke-1 tanggal 15 Jan 2026
MR-20260115-002  → Rekam medis ke-2 tanggal 15 Jan 2026
MR-20260116-001  → Rekam medis ke-1 tanggal 16 Jan 2026
```

---

## 🧠 Long-Term Memory

Sistem menyimpan riwayat pasien di ChromaDB. Ketika pasien yang sama datang kembali, agent otomatis mendapat konteks kunjungan sebelumnya:

```
📋 Riwayat pasien Budi Santoso (3 kunjungan terakhir):
  - 2026-01-10: Demam dan batuk → Belum ditegakkan
  - 2026-01-05: Pusing kepala → Belum ditegakkan
  - 2025-12-20: Kontrol rutin → Belum ditegakkan
```

---

## 🛡️ Aturan Keamanan

- **No Hallucination**: Field kosong → `null`, tidak pernah dikarang
- **No Diagnosis**: Agent hanya catat keluhan, bukan tentukan diagnosis
- **Confidence Score**: Field dengan score < 0.5 otomatis diberi flag ⚠️
- **Konfirmasi Wajib**: Data tidak tersimpan sebelum user konfirmasi preview

---

## ⚙️ Environment Variables

| Variable | Deskripsi | Default |
|----------|-----------|---------|
| `OPENAI_API_KEY` | OpenAI API key | — |
| `GOOGLE_SHEETS_SPREADSHEET_ID` | ID spreadsheet target | — |
| `GOOGLE_SHEETS_SHEET_NAME` | Nama sheet tab | `Sheet1` |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | Path ke service account JSON | — |
| `TWILIO_ACCOUNT_SID` | Twilio Account SID | — |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token | — |
| `TWILIO_WHATSAPP_FROM` | Nomor WhatsApp Twilio | `whatsapp:+14155238886` |
| `CHROMA_PERSIST_DIR` | Direktori ChromaDB | `./data/chroma` |
| `TIMEZONE` | Timezone untuk tanggal | `Asia/Jakarta` |
| `APP_HOST` | Host server | `0.0.0.0` |
| `APP_PORT` | Port server | `8000` |
