# Security & Privacy

- Never commit `.env`, tokens, API keys, patient exports, raw PDFs, or local vector databases.
- Restrict WhatsApp webhook access with an explicit authorized-number allowlist.
- Treat phone numbers, patient names, medical record IDs and clinical notes as sensitive data.
- Keep patient-history retrieval read-only and scoped to the minimum context needed.
- Do not use old history to infer current diagnosis, symptoms, treatment, or medication.
- Do not let the LLM generate Medical Record IDs.
- Require explicit preview confirmation before CREATE/UPDATE writes.
- Writer is the only agent that should have Google Sheets write tools.
- Production should add HTTPS, webhook signature verification, audit logging, access controls, retention policy, and encrypted managed storage.
