import peewee_models
import pydantic_models


async def post_card(request: pydantic_models.Card):
    card = await peewee_models.Card.get_or_none(peewee_models.Card.card_id == request.card_id)
    if card is None:
        card = await peewee_models.Order.create(**request.dict())
    else:
        await card.update(**request.dict())
    return card