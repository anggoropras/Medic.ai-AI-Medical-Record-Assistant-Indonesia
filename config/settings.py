from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    whatsapp_business_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = ""
    langflow_api_url: str = "http://localhost:7860"
    langflow_flow_id: str = ""
    langflow_api_key: str = ""
    authorized_phone_numbers: str = ""
    vector_db_url: str = ""
    vector_db_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    google_sheets_id: str = ""
    openai_api_key: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def authorized(self, sender: str) -> bool:
        allowed = {x.strip() for x in self.authorized_phone_numbers.split(",") if x.strip()}
        return sender in allowed

settings = Settings()
