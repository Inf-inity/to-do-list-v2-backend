from datetime import timedelta

from fastapi import APIRouter, Depends, Query, Request
from fastapi.security import OAuth2PasswordRequestForm

from database import db, select
from models.user import User
from schemas.user import User as Us
from schemas.token import Token
from utils.auth import admin_auth, create_access_token, get_token, user_auth
from utils.environment import ACCESS_TOKEN_EXPIRE_MINUTES
from utils.exceptions import AccountDisabled, InvalidCredentials, InvalidPassword, InvalidUser, NameDuplicated, PermissionDeniedError
from utils.crypt import hash_password, verify_password


router = APIRouter(tags=["/users"])


@router.post("/token", response_model=Token)
async def login(data_form: OAuth2PasswordRequestForm = Depends()):
    if not (user := await User.get_user_by_name(data_form.username)) or not verify_password(user.password, data_form.password):
        raise InvalidCredentials
    if not user.enabled:
        raise AccountDisabled

    access_token = create_access_token(
        data={"sub": user.name}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    await user.create_session(access_token)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/users/new")
async def register(user: Us):
    if await User.get_user_by_name(user.name):
        raise NameDuplicated

    user = await User.create(user.name, hash_password(user.password), user.enabled, user.admin)
    return user.serialize


@router.get("/users/all", dependencies=[admin_auth])
async def all_users(
    enabled: bool | None = Query(None),
    admin: bool | None = Query(None),
):
    # noinspection PyTypeChecker
    query = select(User, User.tasks)
    if enabled is not None:
        query = query.where(User.enabled == enabled)
    if admin is not None:
        query = query.where(User.admin == admin)

    return {"users": [user.serialize async for user in await db.stream(query.order_by(User.id))]}


@router.delete("/users/delete", dependencies=[user_auth])
async def delete_task(request: Request, user_id: int):
    exc_user = await User.get_user_by_token(get_token(request))
    user = await db.get(User, id=user_id)
    if not user:
        raise InvalidUser

    if (user == exc_user) or exc_user.admin and not user.admin:
        await user.remove()
        return True
    else:
        raise PermissionDeniedError


@router.get("/users/me", dependencies=[user_auth])
async def get_me(request: Request):
    return (await User.get_user_by_token(get_token(request))).serialize


@router.post("/users/edit/name", dependencies=[user_auth])
async def edit_user_name(request: Request, name: str):
    exc_user = await User.get_user_by_token(get_token(request))

    if await User.get_user_by_name(name):
        raise NameDuplicated

    exc_user.name = name
    return exc_user.serialize


@router.post("/users/edit/password", dependencies=[user_auth])
async def edit_user_password(request: Request, old_pw: str, new_pw):
    exc_user = await User.get_user_by_token(get_token(request))

    if not verify_password(exc_user.password, old_pw):
        raise InvalidPassword

    exc_user.password = hash_password(new_pw)
    return True
