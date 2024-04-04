from fastapi import HTTPException

import peewee_models
import pydantic_models


async def get_autotext():
    return [record.to_dict() for record in await peewee_models.Autotext.select()]


async def post_autotext(request: pydantic_models.CreateAutotext):
    await peewee_models.Autotext.create(priority=request.priority, title=request.title, message=request.message)


async def put_autotext(request: pydantic_models.EditAutotext):
    try:
        autotext = [atext for atext in await peewee_models.Autotext.select() if atext.id == request.id][0]
        autotext.priority = request.priority
        autotext.title = request.title
        autotext.message = request.message
        await autotext.save()
        return True
    except:
        raise HTTPException(status_code=404)

async def delete_autotext(_id: int):
    autotext = await peewee_models.Autotext.get_or_none(peewee_models.Autotext.id == _id)
    if autotext:
        await autotext.delete_instance()
    else:
        raise HTTPException(status_code=404, detail="Autotext not found")
