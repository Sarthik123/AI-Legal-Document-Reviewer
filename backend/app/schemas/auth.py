from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(
        min_length=8,
        max_length=128,
    )


class UserResponse(BaseModel):
    id: str
    email: EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str


class MessageResponse(BaseModel):
    message: str


class RegistrationResponse(MessageResponse):
    verification_required: bool


class EmailAddressRequest(BaseModel):
    email: EmailStr


class EmailTokenRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)


class PasswordResetRequest(EmailAddressRequest):
    pass


class PasswordResetConfirm(EmailTokenRequest):
    password: str = Field(min_length=8, max_length=128)
