from fastapi import FastAPI, HTTPException, Request
from .config import settings
from .langflow_client import run_flow
from .whatsapp_client import send_text

app = FastAPI(title="Medic.ai WhatsApp Gateway")

@app.get("/webhook")
async def verify(mode: str | None = None, challenge: str | None = None, verify_token: str | None = None):
    if mode == "subscribe" and verify_token == settings.whatsapp_verify_token and challenge:
        return int(challenge)
    raise HTTPException(status_code=403, detail="Webhook verification failed")

@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()
    messages = body.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {}).get("messages", [])
    for message in messages:
        sender = message.get("from")
        text = message.get("text", {}).get("body")
        if not sender or not text:
            continue
        if not settings.authorized(sender):
            await send_text(sender, "Nomor ini belum terdaftar sebagai pengguna Medic.ai yang berwenang.")
            continue
        reply = await run_flow(text, f"wa:{sender}")
        await send_text(sender, reply)
    return {"ok": True}
