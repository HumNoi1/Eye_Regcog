from fastapi import APIRouter, Depends
from ..schemas import ChallengeResponse, VerifyEyeRequest, VerifyEyeResult, TokenRequest, TokenResponse
from ..utils.nonce import issue_nonce, consume_nonce
from ..utils.image import base64_to_numpy
from ..services.inference import predict_identity
from ..services.supabase_svc import map_label_to_user_id, log_event
from ..deps import get_supabase
from jose import jwt
from ..config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/challenge", response_model=ChallengeResponse)
async def challenge():
    nonce, ttl = issue_nonce()
    return ChallengeResponse(nonce=nonce, expires_in_sec=ttl)


@router.post("/verify-eye", response_model=VerifyEyeResult)
async def verify_eye(req: VerifyEyeRequest, supabase=Depends(get_supabase)):
    # ตรวจ nonce
    if not consume_nonce(req.nonce):
        return VerifyEyeResult(verified=False, reason="nonce_invalid_or_expired")

    # แปลงภาพ
    image = base64_to_numpy(req.image_base64)

    # infer หาตัวตน
    label, conf = predict_identity(image)
    if not label or conf is None:
        log_event(supabase, None, 0.0, result="fail")
        return VerifyEyeResult(verified=False, reason="no_match")


    user_id = map_label_to_user_id(supabase, label)
    if not user_id:
        log_event(supabase, None, float(conf), result="fail")
        return VerifyEyeResult(verified=False, reason="label_not_mapped")


    log_event(supabase, user_id, float(conf), result="success")
    return VerifyEyeResult(verified=True, identity_label=label, user_id=user_id, confidence=float(conf))


@router.post("/token", response_model=TokenResponse)
async def token(req: TokenRequest):
    # เดโม: ออก JWT แบบง่าย ๆ (ไม่มีการตรวจสอบซับซ้อน)
    payload = {"sub": req.user_id}
    encoded = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    return TokenResponse(access_token=encoded)