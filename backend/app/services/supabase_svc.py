from typing import Optional
from supabase import Client

USERS_TABLE = "users"
IDENTITIES_TABLE = "identities"
EVENTS_TABLE = "login_events"

def map_label_to_user_id(supabase: Client, identity_label: str) -> Optional[str]:
    # คาดว่ามีตาราง identities: { identity_label, user_id }
    res = supabase.table(IDENTITIES_TABLE).select("user_id").eq("identity_label", identity_label).maybe_single().execute()
    data = getattr(res, 'data', None)
    if data and isinstance(data, dict):
        return data.get("user_id")
    return None




def log_event(supabase: Client, user_id: Optional[str], confidence: float, result: str, method: str = "eye-login") -> None:
    supabase.table(EVENTS_TABLE).insert({
        "user_id": user_id,
        "confidence": confidence,
        "result": result,
        "method": method,
    }).execute()