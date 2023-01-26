from datetime import datetime
from pydantic import BaseModel, EmailStr, constr


class UserBaseSchema(BaseModel):
    username: str
    email: EmailStr
    photo: str

    class Config:
        orm_mode = True


class CreateUserSchema(UserBaseSchema):
    password: constr(min_length=8)
    passwordConfirm: str


class LoginUserSchema(BaseModel):
    email: EmailStr
    password: str


class UserResponseSchema(UserBaseSchema):
    id: str
    pass


class UserResponse(BaseModel):
    status: str
    user: UserResponseSchema


class ResetPasswordRequestSchema(BaseModel):
    email: EmailStr


class ResetPasswordSchema(BaseModel):
    password: constr(min_length=8)
    passwordConfirm: constr(min_length=8)


class ChangePasswordSchema(BaseModel):
    currentPassword: constr(min_length=8)
    newPassword: constr(min_length=8)
    passwordConfirm: constr(min_length=8)
