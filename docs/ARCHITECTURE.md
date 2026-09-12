# Medic.ai Architecture

```text
WhatsApp Business API
        |
        v
whatsapp_webhook (auth + session mapping)
        |
        v
LangFlow Flow
 Extractor -> Validator -> Preview/Confirm -> Writer
                         |
                  status != Lengkap
                         |
                     Chat Output

Writer -> Google Sheets -> sync_after_sheet_write -> patient memory
```

- Extractor: JSON extraction only; no tools.
- Validator: standardization/validation only; no tools.
- Writer: only component allowed to write to Sheets.
- Patient history: read-only context before CREATE; never auto-populates a new visit.
- Medical Record ID: application-generated, never LLM-generated.

The existing LangFlow system prompt/rules remain the source of truth. These modules provide integration boundaries and do not replace clinical safety rules.
