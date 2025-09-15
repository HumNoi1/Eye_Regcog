from supabase import create_client, Client
from .config import settings

def get_supabase() -> Client:
    url = settings.SUPABASE_URL
    key = settings.SUPABASE_SERVICE_ROLE_KEY  # service role only (backend)
    return create_client(url, key)
