from dataclasses import dataclass
from typing import Optional
from uuid import UUID

import app.exceptions as exc
import app.persistence.database as db
import app.persistence.email as email
from app.base.enums import GenderType, RoleType
from app.utils import Response
from app.utils.security import encode_jwt, hash_password, verify_password
from fastapi import APIRouter, responses
from pydantic import BaseModel, EmailStr

router = APIRouter(tags=['Public'])


@router.get('/', status_code=200, response_class=responses.HTMLResponse)
async def default_page():
    return '<a href="/docs">/docs</a>'


class HealthCheckOutput(BaseModel):
    health: Optional[str] = 'ok'


@router.get('/health')
async def health_check() -> Response[HealthCheckOutput]:
    return Response(data=HealthCheckOutput(health='ok'))


class LoginInput(BaseModel):
    email: EmailStr
    password: str


@dataclass
class LoginOutput:
    account_id: int
    token: str


@router.post('/login', tags=['Account'])
async def login(data: LoginInput) -> Response[LoginOutput]:
    try:
        account_id, pass_hash, role = await db.account.read_by_email(email=data.email)
    except TypeError:
        raise exc.LoginFailed

    if not verify_password(data.password, pass_hash):
        raise exc.LoginFailed

    token = encode_jwt(account_id=account_id)
    return Response(data=LoginOutput(account_id=account_id, token=token))


class EmailVerificationOutput(BaseModel):
    success: bool = True


@router.get('/email-verification', tags=['Email Verification'])
@router.post('/email-verification', tags=['Email Verification'])
async def email_verification(code: UUID) -> Response[EmailVerificationOutput]:
    await db.email_verification.verify_email(code=code)
    return Response(data=EmailVerificationOutput(success=True))


@dataclass
class AddAccountOutput:
    id: int


class AddAccountInput(BaseModel):
    email: EmailStr
    password: str
    nickname: str
    gender: GenderType
    role: RoleType


@router.post('/account', tags=['Account'])
async def add_account(data: AddAccountInput) -> Response[AddAccountOutput]:
    try:
        account_id = await db.account.add(
            email=data.email,
            pass_hash=hash_password(data.password),
            nickname=data.nickname,
            gender=data.gender,
            role=data.role,
            is_google_login=False,
        )
    except exc.UniqueViolationError:
        raise exc.EmailExists
    code = await db.email_verification.add(account_id=account_id, email=data.email)
    await email.verification.send(to=data.email, code=str(code))
    return Response(data=AddAccountOutput(id=account_id))


class ResendEmailVerificationInput(BaseModel):
    email: EmailStr


@router.post('/email-verification/resend', tags=['Email Verification'])
async def resend_email_verification(data: ResendEmailVerificationInput):
    account_id, *_ = await db.account.read_by_email(email=data.email)
    code = await db.email_verification.read(account_id=account_id, email=data.email)
    await email.verification.send(to=data.email, code=str(code))
    return Response(data=EmailVerificationOutput(success=True))


class ForgetPasswordInput(BaseModel):
    email: EmailStr


@router.post('/forget-password', tags=['Account'])
async def forget_password(data: ForgetPasswordInput) -> Response:
    account_id, *_ = await db.account.read_by_email(email=data.email)
    code = await db.email_verification.add(account_id=account_id, email=data.email)
    await email.forget_password.send(to=data.email, code=str(code))
    return Response()


class ResetPasswordInput(BaseModel):
    code: str
    password: str


@router.post('/reset-password', tags=['Account'])
async def reset_password(data: ResetPasswordInput) -> Response:
    await db.account.reset_password(code=data.code, pass_hash=hash_password(data.password))
    return Response()
