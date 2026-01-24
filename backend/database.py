from supabase import create_client, Client
from config import config

def get_supabase_client() -> Client:
    return create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)

supabase = get_supabase_client()
