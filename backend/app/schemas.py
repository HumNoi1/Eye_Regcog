from pydantic import BaseModel, EmailStr, Field

# --- Requests ---
class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    email: EmailStr
    password: str = Field(min_length=6)

class LoginRequest(BaseModel):
    identifier: str  # email หรือ username
    password: str

# --- Responses ---
class UserOut(BaseModel):
    id: str
    username: str
    email: EmailStr

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class AuthResponse(BaseModel):
    user: UserOut
    token: TokenOut
