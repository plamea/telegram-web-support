import asyncio

from fastapi import HTTPException

import peewee_models


async def processing():
    try:
        while True:
            for user in await peewee_models.User.select().where(peewee_models.User.turn == False):
                tickets = [ticket for ticket in await peewee_models.Ticket.select().where(peewee_models.Ticket.operator == user.username)]
                for ticket in tickets:
                    ticket.operator = None
                    await ticket.save()
            for ticket in await peewee_models.Ticket.select().where(peewee_models.Ticket.operator == None):
                users = [u for u in await peewee_models.User.select().where(peewee_models.User.turn == True)]
                if len(users) == 0:
                    break
                count_of_tickets = [(u.username, await peewee_models.Ticket.select().where(peewee_models.Ticket.operator == u.username).count()) for u in users]
                count_of_tickets.sort(key=lambda x: x[1])
                ticket.operator = count_of_tickets[0][0]
                await ticket.save()
            await asyncio.sleep(0)
    except:
        print("EXITED\n\n\n\n\n\n\n")


async def get_tickets(user: peewee_models.User):
    tickets = []
    if user.role == 2:
        for i in await peewee_models.Ticket.select(
                peewee_models.Ticket.uu_id,
                peewee_models.Ticket.client_username,
                peewee_models.Ticket.is_last_answer_from_operator,
                peewee_models.Ticket.operator,
                peewee_models.Ticket.status,
                peewee_models.Ticket.date_of_request,
                peewee_models.Ticket.date_of_last_change
        ).where(
            peewee_models.Ticket.operator == user.username
            #peewee_models.Ticket.status.in_(["new", "in_work", "pending"])
        ):
            order = await peewee_models.Order.get_or_none(peewee_models.Order.uu_id == str(i.uu_id))
            operator = await peewee_models.User.get_or_none(peewee_models.User.username == i.operator)
            tickets.append(
                {
                    "uu_id": i.uu_id,
                    "client_username": i.client_username,
                    "is_last_answer_from_operator": i.is_last_answer_from_operator,
                    "operator": operator.displayableName if operator else None,
                    "date_of_request": i.date_of_request,
                    "date_of_last_change": i.date_of_last_change,
                    "ticket_status": i.status,
                    "order_status": order.status if order else None,
                    "masked_card_number": order.masked_card_number if order else None,
                    "amount": order.amount if order else None,
                    "source": order.source if order else None,
                    "currency": order.currency if order else None, 
                    "isP2PCard": order.isP2PCard if order else None
                }
            )
        return tickets
    elif user.role < 2:
        for i in await peewee_models.Ticket.select(
                peewee_models.Ticket.uu_id,
                peewee_models.Ticket.client_username,
                peewee_models.Ticket.is_checked,
                peewee_models.Ticket.is_last_answer_from_operator,
                peewee_models.Ticket.operator,
                peewee_models.Ticket.status,
                peewee_models.Ticket.date_of_request,
                peewee_models.Ticket.date_of_last_change
        ):
            order = await peewee_models.Order.get_or_none(peewee_models.Order.uu_id == str(i.uu_id))
            operator = await peewee_models.User.get_or_none(peewee_models.User.username == i.operator)
            tickets.append(
                {
                    "uu_id": i.uu_id,
                    "client_username": i.client_username,
                    "is_checked": i.is_checked,
                    "is_last_answer_from_operator": i.is_last_answer_from_operator,
                    "operator": operator.displayableName if operator else None,
                    "date_of_request": i.date_of_request,
                    "date_of_last_change": i.date_of_last_change,
                    "ticket_status": i.status,
                    "order_status": order.status if order else None,
                    "masked_card_number": order.masked_card_number if order else None,
                    "amount": order.amount if order else None,
                    "source": order.source if order else None,
                    "currency": order.currency if order else None,
                    "isP2PCard": order.isP2PCard if order else None
                }
            )
        return tickets
    raise HTTPException(403)


async def post_ticket(request):
    await peewee_models.Ticket.create(
        uu_id=request.uu_id,
        client_username=request.username,
        date_of_request=request.date_of_request,
        date_of_last_change=request.date_of_last_change
    )
