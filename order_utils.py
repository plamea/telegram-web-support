import peewee_models
import pydantic_models


async def post_order(request: pydantic_models.Order):
    order = await peewee_models.Order.get_or_none(peewee_models.Order.uu_id == request.uu_id)
    if order is None:
        order = await peewee_models.Order.create(**request.dict())
    else:
        await order.update(**request.dict())
    return order.to_dict()


async def get_orders():
    return [order.to_dict() for order in await peewee_models.Order.select()]


async def get_order(_id: str):
    order_or_none = await peewee_models.Order.get_or_none(peewee_models.Order.uu_id == _id)
    if order_or_none is None:
        return {
            "error": "Not Found"
        }
    order: peewee_models.Order = order_or_none
    return {
        "result": "ok",
        "order": {
            "uu_id": order.uu_id,
            "amount": order.amount,
            "status": order.status,
            "create_time": order.create_time,
            "card_number": order.card_number,
            "masked_card_number": order.masked_card_number,
            "source": order.source,
            "currency": order.currency,
            "isP2PCard": order.isP2PCard,
            "remove_time": order.remove_time,
            "pay_time": order.pay_time,
            "card_id": order.card_id
        }
    }
    
