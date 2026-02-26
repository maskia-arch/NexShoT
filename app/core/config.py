from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Datenbank
    SUPABASE_URL: str
    SUPABASE_KEY: str

    # Master Bot & Server Konfiguration
    MASTER_BOT_TOKEN: str
    WEBHOOK_HOST: str
    PORT: int = 8000
    
    # Dashboard Security (Login-Schutz)
    ADMIN_SECRET: str = "changeme" 

    # Super Admin ID (Hier kommt deine Telegram-ID rein für Benachrichtigungen)
    ADMIN_TELEGRAM_ID: int

    # Security (Für die Verschlüsselung der Shop-Bot-Tokens)
    # Muss ein 32-byte url-safe base64 string sein
    ENCRYPTION_KEY: str

    class Config:
        env_file = ".env"

settings = Settings()
