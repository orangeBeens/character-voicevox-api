from typing import List

from pydantic import BaseModel, Field


class TextRequest(BaseModel):
    text: str = Field(..., min_length=1)
    speaker_id: int = Field(..., ge=0)
    volume_scale: float = Field(2.0, ge=0.5, le=10.0)
    speed_scale: float = Field(1.0, ge=0.5, le=2.0)
    pitch_scale: float = Field(0.0, ge=-0.15, le=0.15)
    intonation_scale: float = Field(0.0, ge=0.0, le=3.0)
    pre_phoneme_length: float = Field(0.1, ge=-5.0, le=10.0)
    post_phoneme_length: float = Field(0.0, ge=0.0, le=10.0)


class ManzaiRequest(BaseModel):
    title: str
    combi_name: str
    left_chara: str
    right_chara: str
    left_chara_path: str
    right_chara_path: str
    voices: List[TextRequest]
