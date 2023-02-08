# routers/auth.py
import hashlib
from datetime import datetime, timedelta
from random import randbytes
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from pydantic import EmailStr
from app import oauth2
from app.database import User
from app.email import Email
from app.serializers.userSerializers import userEntity, userLogin
from app.oauth2 import AuthJWT
from app.config import settings
from fastapi.security import OAuth2PasswordRequestForm
from .. import schemas, utils

router = APIRouter()
ACCESS_TOKEN_EXPIRES_IN = settings.ACCESS_TOKEN_EXPIRES_IN
REFRESH_TOKEN_EXPIRES_IN = settings.REFRESH_TOKEN_EXPIRES_IN


@router.post('/register', status_code=status.HTTP_201_CREATED)
async def create_user(payload: schemas.CreateUserSchema, request: Request):
    # Check if user or username already exist
    email = User.find_one({'email': payload.email.lower()})
    username = User.find_one({'username': payload.username})
    if username:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail='Username already exists')
    if email:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail='Email already exists')
    # Compare password and passwordConfirm
    if payload.password != payload.passwordConfirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='Passwords do not match')
    # Hash the password
    payload.password = utils.hash_password(payload.password)
    del payload.passwordConfirm
    payload.email = payload.email.lower()
    payload.full_name = payload.full_name

    result = User.insert_one(payload.dict())
    new_user = User.find_one({'_id': result.inserted_id})
    try:
        token = randbytes(10)
        hashedCode = hashlib.sha256()
        hashedCode.update(token)
        verification_code = hashedCode.hexdigest()
        User.find_one_and_update({"_id": result.inserted_id}, {
            "$set": {
                "verification": {
                    "code": verification_code,
                    "expiration": datetime.utcnow() + timedelta(days=3)
                },
                "role": "user",
                "verified": False,
                "updated_at": datetime.utcnow(),
                "created_at": datetime.utcnow()
            }
        })

        # url = f"{request.url.scheme}://{request.client.host}:{request.url.port}/api/auth/verifyemail/{token.hex()}"
        url = f"{request.url.scheme}://{settings.BASE_URL}/api/auth/verifyemail/{token.hex()}"
        await Email(userEntity(new_user), url, [EmailStr(payload.email)]).sendVerificationCode()
    except Exception as error:
        User.find_one_and_update({"_id": result.inserted_id}, {
            "$set": {"verification_code": None, "updated_at": datetime.utcnow()}})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail='There was an error sending email')
    return {'status': 'success', 'message': 'Verification token successfully sent to your email'}


@router.post('/login')
async def login(payload: schemas.LoginUserSchema, request: Request, response: Response, Authorize: AuthJWT = Depends()):
    # Check if the user exist
    db_user = User.find_one({'email': payload.email.lower()})
    if not db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='Incorrect Email or Password')
    user = userLogin(db_user)
    # Check if user verified his email
    if not user['verified']:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Please verify your email address')
    # Check if the password is valid
    if not utils.verify_password(payload.password, user['password']):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='Incorrect Email or Password')
    # Extract device information from request headers or user agent
    device_info = utils.extract_device_info(request)
    # Check if the device is already in the database
    if not User.find_one({"_id": db_user["_id"], "device.user_agent": device_info["user_agent"]}):
        User.find_one_and_update(
            {"_id": db_user["_id"]}, {"$push": {"device": {"$each": [device_info]}}}, upsert=True)
    # Create access token
    access_token = Authorize.create_access_token(
        subject=str(user["id"]), expires_time=timedelta(minutes=ACCESS_TOKEN_EXPIRES_IN))
    # Create refresh token
    refresh_token = Authorize.create_refresh_token(
        subject=str(user["id"]), expires_time=timedelta(minutes=REFRESH_TOKEN_EXPIRES_IN))
    # Store refresh and access tokens in cookie
    response.set_cookie('access_token', access_token, ACCESS_TOKEN_EXPIRES_IN * 60,
                        ACCESS_TOKEN_EXPIRES_IN * 60, '/', None, False, True, 'lax')
    response.set_cookie('refresh_token', refresh_token,
                        REFRESH_TOKEN_EXPIRES_IN * 60, REFRESH_TOKEN_EXPIRES_IN * 60, '/', None, False, True, 'lax')
    response.set_cookie('logged_in', 'True', ACCESS_TOKEN_EXPIRES_IN * 60,
                        ACCESS_TOKEN_EXPIRES_IN * 60, '/', None, False, False, 'lax')
    return {"status": "success", "access_token": access_token, "refresh_token": refresh_token}


@router.post('/refresh')
async def refresh_token(response: Response, Authorize: AuthJWT = Depends()):
    try:
        Authorize.jwt_refresh_token_required()

        user_id = Authorize.get_jwt_subject()
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail='Could not refresh access token')
        user = userEntity(User.find_one({'_id': ObjectId(str(user_id))}))
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail='The user belonging to this token no logger exist')
        access_token = Authorize.create_access_token(
            subject=str(user["id"]), expires_time=timedelta(minutes=ACCESS_TOKEN_EXPIRES_IN))
    except Exception as e:
        error = e.__class__.__name__
        if error == 'MissingTokenError':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail='Please provide refresh token')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    response.set_cookie('access_token', access_token, ACCESS_TOKEN_EXPIRES_IN * 60,
                        ACCESS_TOKEN_EXPIRES_IN * 60, '/', None, False, True, 'lax')
    response.set_cookie('logged_in', 'True', ACCESS_TOKEN_EXPIRES_IN * 60,
                        ACCESS_TOKEN_EXPIRES_IN * 60, '/', None, False, False, 'lax')
    return {'access_token': access_token}


@router.get('/verifyemail/{token}')
async def verify_email(token: str):
    try:
        # Check if token is a hexadecimal
        bytes.fromhex(token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='Invalid token')

    verification_code = hashlib.sha256(bytes.fromhex(token)).hexdigest()
    user = User.find_one({"verification.code": verification_code})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail='Verification code not found')

    # Check if token is expired
    if user["verification"]["expiration"] < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_410_GONE,
                            detail='Token expired')

    User.find_one_and_update({"_id": user['_id']}, {
        "$set": {"verified": True, "updated_at": datetime.utcnow()},
        "$unset": {"verification": ""}})

    return {'status': 'success', 'message': 'Email successfully verified'}


@router.post("/resetpassword", status_code=status.HTTP_200_OK)
async def reset_password_request(payload: schemas.ResetPasswordRequestSchema, request: Request):
    user = User.find_one({'email': payload.email.lower()})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='User not found')
    try:
        token = randbytes(10)
        hashedCode = hashlib.sha256()
        hashedCode.update(token)
        password_reset_code = hashedCode.hexdigest()
        password_expiration_days = 3
        User.find_one_and_update({'_id': user['_id']}, {
            "$set": {"password_reset": {"code": password_reset_code, "expiration": datetime.utcnow() + timedelta(days=password_expiration_days)}, "updated_at": datetime.utcnow()}})
        url = token.hex()
        await Email(userEntity(user), url, [EmailStr(payload.email)]).sendPasswordResetCode()
    except Exception as error:
        User.find_one_and_update({'_id': user['_id']}, {
            "$unset": {"password_reset": ""}})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail='There was an error sending email')
    return {'status': 'success', 'message': 'Password reset code sent to your email'}


@router.post("/resetpassword/{token}", status_code=status.HTTP_200_OK)
async def reset_password_confirm(token: str, payload: schemas.ResetPasswordSchema):
    hashed_code = hashlib.sha256()
    hashed_code.update(bytes.fromhex(token))
    password_reset_code = hashed_code.hexdigest()

    user = User.find_one({"password_reset.code": password_reset_code})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The specified password reset code is invalid.")

    if payload.password != payload.passwordConfirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password and password confirmation do not match.")

    if user['password_reset']['expiration'] < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset code expired.")

    hashed_password = utils.hash_password(payload.password)
    User.find_one_and_update(
        {"_id": user["_id"]},
        {
            "$unset": {
                "password_reset": ""
            },
            "$set": {
                "password": hashed_password,
                "updated_at": datetime.utcnow()
            }
        }
    )

    return {"status": "success", "message": "Password successfully reset"}


@router.post("/changepassword", status_code=status.HTTP_200_OK)
async def change_password(payload: schemas.ChangePasswordSchema, user_id: str = Depends(oauth2.require_user)):
    user = User.find_one({'_id': ObjectId(str(user_id))})
    if not utils.verify_password(payload.currentPassword, user['password']):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='Incorrect current password')
    if payload.newPassword != payload.passwordConfirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='Passwords do not match')

    if utils.verify_password(payload.newPassword, user['password']):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='New password cannot be the same as the current password')

    user_data = {
        'password': utils.hash_password(payload.newPassword),
        'updated_at': datetime.utcnow()
    }
    User.update_one({'_id': user['_id']}, {'$set': user_data})
    return {'status': 'success', 'message': 'Password successfully changed'}


@router.get('/logout', status_code=status.HTTP_200_OK)
async def logout(response: Response, Authorize: AuthJWT = Depends(), user_id: str = Depends(oauth2.require_user)):
    Authorize.unset_jwt_cookies()
    response.set_cookie('logged_in', '', -1)

    return {'status': 'success'}
