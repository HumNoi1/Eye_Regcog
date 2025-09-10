from pydantic import BaseModel, Field
from typing import Optional

class ChallengeResponse(BaseModel):
    nonce: str
    expires_in_sec: int

class VerifyEyeRequest(BaseModel):
    image_base64: str = Field(..., description="Base64-encoded image (JPEG/PNG)")
    nonce: str

class VerifyEyeResult(BaseModel):
    verified: bool
    identity_label: Optional[str] = None
    user_id: Optional[str] = None
    confidence: Optional[float] = None
    reason: Optional[str] = None

class TokenRequest(BaseModel):
    user_id: str
    nonce: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"