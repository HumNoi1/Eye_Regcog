from fastapi import APIRouter
import torch
from ..config import settings

router = APIRouter(prefix="/health", tags=["health"])

@router.get("")
def health():
    return {
    "app": settings.APP_NAME,
    "gpu": torch.cuda.is_available(),
    "cuda_device": str(torch.cuda.current_device()) if torch.cuda.is_available() else None,
    }