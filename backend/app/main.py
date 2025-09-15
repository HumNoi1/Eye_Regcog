# app/main.py
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from .config import settings
from .db import get_supabase
from .security import hash_password, verify_password, create_access_token, decode_token
from .schemas import RegisterRequest, LoginRequest, UserOut, AuthResponse

app = FastAPI(title="Auth API (FastAPI + Supabase)")

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ALLOW_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------- Helpers --------
def find_user_by_identifier(sb, identifier: str):
    # ลองหาแบบ email ก่อน (case-insensitive, เทียบตรงตัว)
    resp = sb.table("users").select("*").ilike("email", identifier).execute()
    if resp.data:
        return resp.data[0]
    # ถ้าไม่เจอ email ลอง username (case-insensitive)
    resp2 = sb.table("users").select("*").ilike("username", identifier).execute()
    if resp2.data:
        return resp2.data[0]
    return None

def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_token(token)
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return {"sub": sub}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# -------- Routes --------

@app.post("/auth/register", response_model=AuthResponse)
def register(body: RegisterRequest):
    sb = get_supabase()

    # เช็คซ้ำ username/email แบบ case-insensitive (ไม่ใช้ lower(...) ในตัวกรอง)
    exists = (
        sb.table("users")
        .select("id")
        .or_(f"username.ilike.{body.username},email.ilike.{body.email}")
        .execute()
    )
    if exists.data:
        raise HTTPException(status_code=409, detail="Username or email already exists")

    # hash รหัสผ่าน
    password_hash = hash_password(body.password)

    # --- วิธีที่ 2: insert แล้ว select อีกรอบด้วย id ---
    insert_resp = (
        sb.table("users")
        .insert({
            "username": body.username,
            "email": body.email,
            "password_hash": password_hash,
        })
        .execute()
    )

    if not insert_resp.data or len(insert_resp.data) == 0:
        # ปกติ Supabase จะคืน row (อย่างน้อยมี id) กลับมา ให้ดักกรณีผิดปกติไว้
        raise HTTPException(status_code=500, detail="Insert failed")

    new_id = insert_resp.data[0].get("id")
    if not new_id:
        # ถ้าไม่คืน id มาก็ถือว่าผิดปกติ
        raise HTTPException(status_code=500, detail="Insert returned no id")

    # select อีกรอบเพื่อเอา row เต็ม ๆ
    user_q = sb.table("users").select("*").eq("id", new_id).single().execute()
    if not user_q.data:
        raise HTTPException(status_code=500, detail="Cannot fetch inserted user")

    user_row = user_q.data
    token = create_access_token(sub=user_row["id"], extra={"username": user_row["username"]})

    return {
        "user": {
            "id": user_row["id"],
            "username": user_row["username"],
            "email": user_row["email"],
        },
        "token": {
            "access_token": token,
            "token_type": "bearer",
        }
    }

@app.post("/auth/login", response_model=AuthResponse)
def login(body: LoginRequest):
    sb = get_supabase()

    user_row = find_user_by_identifier(sb, body.identifier)
    if not user_row:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(body.password, user_row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(sub=user_row["id"], extra={"username": user_row["username"]})
    return {
        "user": {
            "id": user_row["id"],
            "username": user_row["username"],
            "email": user_row["email"],
        },
        "token": {
            "access_token": token,
            "token_type": "bearer",
        }
    }

@app.get("/auth/me", response_model=UserOut)
def me(current = Depends(get_current_user)):
    sb = get_supabase()
    uid = current["sub"]
    resp = sb.table("users").select("*").eq("id", uid).single().execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="User not found")
    u = resp.data
    return {"id": u["id"], "username": u["username"], "email": u["email"]}
