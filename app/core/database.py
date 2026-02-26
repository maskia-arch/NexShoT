from supabase import create_client, Client
from app.core.config import settings

# Erstellt eine einzige Instanz für die gesamte App
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
