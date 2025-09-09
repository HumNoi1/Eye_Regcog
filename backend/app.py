import os, numpy as np, cv2
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from utils.auth import verify_supabase_jwt
from utils.face import detect_and_embed, best_score, COSINE_THRESHOLD
from utils.supa import insert_embeddings, get_user_embeddings

ALLOWED = os.getenv("ALLOWED_ORIGINS","http://localhost:3000").split(",")

app = FastAPI(title="Face API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

class VerifyResp(BaseModel):
    ok: bool
    score: float | None = None
    msg: str

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.post("/face/enroll/commit")
async def enroll_commit(images: list[UploadFile] = File(...), user=Depends(verify_supabase_jwt)):
    embs = []
    for f in images:
        data = await f.read()
        img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        if img is None: raise HTTPException(400, "bad image")
        emb = detect_and_embed(img)
        if emb is not None:
            embs.append(emb.tolist())
    if len(embs) < 3:
        raise HTTPException(400, "need >=3 valid face frames")
    quality = 1.0  # placeholder: คำนวนจริงทีหลังได้
    await insert_embeddings(user["_token"], user["sub"], embs, quality)
    return {"ok": True, "templates": len(embs), "quality": quality}

@app.post("/face/verify", response_model=VerifyResp)
async def face_verify(image: UploadFile = File(...), user=Depends(verify_supabase_jwt)):
    data = await image.read()
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None: raise HTTPException(400, "bad image")

    probe = detect_and_embed(img)
    if probe is None:
        return VerifyResp(ok=False, score=None, msg="no face")

    gallery = await get_user_embeddings(user["_token"], user["sub"])
    gallery = [np.array(g, dtype="float32") for g in gallery]
    score = best_score(probe, gallery)
    ok = bool(score >= COSINE_THRESHOLD)
    return VerifyResp(ok=ok, score=float(score), msg="ok" if ok else "fail")
