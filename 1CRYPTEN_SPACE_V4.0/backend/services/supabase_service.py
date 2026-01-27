from supabase import create_client, Client
from config import settings

class SupabaseService:
    def __init__(self):
        self.client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

    async def get_banca_status(self):
        response = self.client.table("banca_status").select("*").single().execute()
        return response.data

    async def update_banca_status(self, data: dict):
        response = self.client.table("banca_status").update(data).eq("id", data.get("id")).execute()
        return response.data

    async def get_active_slots(self):
        response = self.client.table("slots_ativos").select("*").execute()
        return response.data

    async def update_slot(self, slot_id: int, data: dict):
        response = self.client.table("slots_ativos").update(data).eq("id", slot_id).execute()
        return response.data

    async def log_signal(self, signal_data: dict):
        response = self.client.table("journey_signals").insert(signal_data).execute()
        return response.data

    async def get_recent_signals(self, limit: int = 100):
        response = self.client.table("journey_signals").select("*").order("timestamp", desc=True).limit(limit).execute()
        return response.data

    async def log_event(self, agent: str, message: str, level: str = "INFO"):
        try:
            data = {"agent": agent, "message": message, "level": level}
            response = self.client.table("system_logs").insert(data).execute()
            return response.data
        except Exception as e:
            # If table doesn't exist, we don't want to crash the whole app
            print(f"Log Error (Table missing?): {e}")
            return None

    async def update_signal_outcome(self, signal_id: int, outcome: bool):
        response = self.client.table("journey_signals").update({"outcome": outcome}).eq("id", signal_id).execute()
        return response.data

    async def get_recent_logs(self, limit: int = 50):
        response = self.client.table("system_logs").select("*").order("timestamp", desc=True).limit(limit).execute()
        return response.data

supabase_service = SupabaseService()
