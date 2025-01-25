from httpx import AsyncClient

from app.core.config import settings
from app.core.errors import VoiceVoxError


class VoicevoxClient:
    def __init__(self, base_url: str = settings.VOICEVOX_URL):
        self.base_url = base_url

    async def create_audio_query(self, text: str, speaker_id: int):
        async with AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/audio_query",
                params={"text": text, "speaker": speaker_id},
            )
            if response.status_code != 200:
                raise VoiceVoxError("Failed to generate audio query")
            return response.json()

    # その他のVOICEVOX関連メソッド
