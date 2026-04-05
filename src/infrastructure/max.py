import httpx
import logging
from src.application.interfaces import MaxSenderInterface


class MaxSender(MaxSenderInterface):
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://platform-api.max.ru"
        self.headers = {"Authorization": f"{self.token}"}

    async def get_me(self) -> dict:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/me", headers=self.headers)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logging.error(f"Failed to connect to Max API: {e}")
                return {}

    async def send_to_client(self, client_id: int, text: str) -> int:
        async with httpx.AsyncClient() as client:
            payload = {
                "user_id": client_id,
                "text": text
            }
            try:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                # Assuming the API returns message ID or similar in some field
                # If not, we return a dummy ID
                res_data = response.json()
                return res_data.get("message_id", 0)
            except Exception as e:
                logging.error(f"Failed to send message via Max API: {e}")
                return 0
