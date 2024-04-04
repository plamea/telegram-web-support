import asyncio
import uuid
from datetime import datetime

from fastapi import HTTPException
from passlib.context import CryptContext

import peewee_models
import pydantic_models

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

online = {}


async def process_users():
    while True:
        try:
            timestamp = datetime.now().timestamp()
            users = await peewee_models.User.select()
            for u in users:
                if u.username in online and timestamp - online[u.username] > 60:
                    online.pop(u.username)
                    u.turn = False
                    await u.save()
                elif u.username in online and u.turn:
                    u.time += timestamp - online[u.username]
                    await u.save()
        except BaseException as e:
            print(e)
        await asyncio.sleep(5)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


async def authenticate_user(username: str, password: str) -> peewee_models.User | None:
    user = await peewee_models.User.get_or_none(peewee_models.User.username == username)
    if not user or not verify_password(password, user.password):
        return None
    return user


async def post_turn(user: peewee_models.User, val: bool):
    user.turn = val
    await user.save()


async def get_turn(user: peewee_models.User):
    return user.turn


async def reset_time(username: str):
    user = await peewee_models.User.get_or_none(peewee_models.User.username == username)
    if user:
        user.time = 0
        await user.save()


async def create_user(username: str, password: str, displayableName: str, role: int,
                      adminID: int | None):
    password_hash = get_password_hash(password)
    _uuid = None
    while True:
        _uuid = uuid.uuid5(uuid.NAMESPACE_X500, f"{username}_{datetime.now().timestamp()}")
        user = await peewee_models.User.get_or_none(peewee_models.User.uuid == str(_uuid))
        if user is None:
            break

    await peewee_models.User.create(uuid=str(_uuid), adminID=adminID if adminID else _uuid.int % (2 ** 15),
                                    username=username, password=password_hash, role=role,
                                    displayableName=displayableName)


async def get_users():
    temp = [user.to_dict() for user in await peewee_models.User.select()]
    for t in temp:
        t["is_online"] = t["username"] in online
    return temp


async def post_users(request: pydantic_models.CreateUser):
    user = await peewee_models.User.get_or_none(peewee_models.User.username == request.username)

    if user:
        raise HTTPException(status_code=409, detail="Username already used")

    if await peewee_models.User.get_or_none(peewee_models.User.adminID == request.adminID) is not None:
        raise HTTPException(status_code=400, detail="Admin ID already used")

    if await peewee_models.User.get_or_none(peewee_models.User.displayableName == request.displayableName) is not None:
        raise HTTPException(status_code=400, detail="Displayable name already used")

    await create_user(request.username, request.password, request.displayableName, request.role, request.adminID)


async def put_users(request: pydantic_models.EditUser):
    u: peewee_models.User | None = await peewee_models.User.get_or_none(peewee_models.User.uuid == request.uuid)

    if u is None:
        raise HTTPException(status_code=404, detail="User not found")

    user = await peewee_models.User.get_or_none(peewee_models.User.adminID == request.adminID)
    if user is not None and user.uuid != request.uuid:
        raise HTTPException(status_code=409, detail="Admin ID already used")

    user = await peewee_models.User.get_or_none(peewee_models.User.displayableName == request.displayableName)
    if user is not None and user.uuid != request.uuid:
        raise HTTPException(status_code=409, detail="Displayable name already used")

    user = await peewee_models.User.get_or_none(peewee_models.User.username == request.username)
    if user is not None and user.uuid != request.uuid:
        raise HTTPException(status_code=409, detail="Username name already used")

    u.adminID = request.adminID
    u.displayableName = request.displayableName
    u.username = request.username
    if request.password:
        u.password = get_password_hash(request.password)
    u.role = request.role
    await u.save()


async def delete_users(username):
    user = await peewee_models.User.get_or_none(peewee_models.User.username == username)
    if user:
        await user.delete_instance()
    else:
        raise HTTPException(status_code=404, detail="User not found")
