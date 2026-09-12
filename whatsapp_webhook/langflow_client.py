import httpx
from .config import settings

async def run_flow(message: str, session_id: str) -> str:
    url = f"{settings.langflow_api_url.rstrip('/')}/api/v1/run/{settings.langflow_flow_id}"
    headers = {"Content-Type": "application/json"}
    if settings.langflow_api_key:
        headers["x-api-key"] = settings.langflow_api_key
    payload = {"input_value": message, "input_type": "chat", "output_type": "chat", "session_id": session_id}
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
    return extract_text(data)

def extract_text(data: dict) -> str:
    outputs = data.get("outputs", [])
    for output in outputs:
        for result in output.get("outputs", []):
            msg = result.get("results", {}).get("message")
            if isinstance(msg, dict) and msg.get("text"):
                return msg["text"]
            if isinstance(msg, str):
                return msg
    return data.get("text") or data.get("message") or "Maaf, respons agent tidak dapat dibaca."
