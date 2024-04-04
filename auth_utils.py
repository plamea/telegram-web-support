from datetime import datetime

from fastapi import HTTPException
from async_fastapi_jwt_auth import AuthJWT

import peewee_models


async def get_user(Authorize: AuthJWT) -> peewee_models.User:
    await Authorize.jwt_required()
    current_user = await Authorize.get_jwt_subject()
    user = await peewee_models.User.get_or_none(peewee_models.User.username == current_user)
    print(user)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def checkAdminPrivileges(Authorize: AuthJWT):
    user = await get_user(Authorize)
    if user.role != 0:
        raise HTTPException(status_code=403, detail="You're not admin")


async def refresh(Authorize: AuthJWT):
    await Authorize.jwt_refresh_token_required()
    print(await Authorize.get_raw_jwt())
    current_user = await Authorize.get_jwt_subject()
    user = await peewee_models.User.get_or_none(peewee_models.User.username == current_user)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if (await Authorize.get_raw_jwt())["jti"] in [rec.token for rec in
                                                  await peewee_models.UsedToken.select(peewee_models.UsedToken.token)]:
        raise HTTPException(status_code=400, detail="Access token already used")
    new_refresh_token = ""
    if (await Authorize.get_raw_jwt())["exp"] - datetime.now().timestamp() < 86_400:
        await peewee_models.UsedToken.create(token=(await Authorize.get_raw_jwt())["jti"])
        new_refresh_token += await Authorize.create_refresh_token(subject=current_user)
    else:
        new_refresh_token += Authorize._token

    new_access_token = await Authorize.create_access_token(subject=current_user)

    return {"access_token": new_access_token, "refresh_token": new_refresh_token}
