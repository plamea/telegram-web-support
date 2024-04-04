import asyncio
import datetime

from async_fastapi_jwt_auth import AuthJWT
from async_fastapi_jwt_auth.exceptions import AuthJWTException, MissingTokenError
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
import pyotp, base64

import auth_utils
import autotext_utils
import bots_utils
import card_utils
import order_utils
import peewee_models
import pydantic_models
import tickets_utils
import user_utils

app = FastAPI()

origins = [
    "http://5.199.168.113",
    "http://5.199.168.113:*",
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # Разрешить все методы запросов
    allow_headers=["*"],  # Разрешить все заголовки
)


@AuthJWT.load_config
def get_config():
    return pydantic_models.Settings()


@app.on_event("startup")
def startup():
    el = asyncio.get_running_loop()
    print(1)
    el.create_task(peewee_models.init_db())
    print(2)
    el.create_task(tickets_utils.processing())
    print(3)
    el.create_task(user_utils.process_users())
    print("STARTED")



@app.exception_handler(AuthJWTException)
def authjwt_exception_handler(request: Request, exc: AuthJWTException):
    print(exc.status_code, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )


@app.post("/online")
async def post_online(Authorize: AuthJWT = Depends()):
    user = await auth_utils.get_user(Authorize)
    user_utils.online[user.username] = datetime.datetime.now().timestamp()


@app.post("/turn")
async def post_turn(state: bool, Authorize: AuthJWT = Depends()):
    user = await auth_utils.get_user(Authorize)
    await user_utils.post_turn(user, state)


@app.get("/turn")
async def get_turn(Authorize: AuthJWT = Depends()):
    user = await auth_utils.get_user(Authorize)
    return await user_utils.get_turn(user)


@app.post("/reset_time")
async def reset_time(username: str, Authorize: AuthJWT = Depends()):
    await auth_utils.checkAdminPrivileges(Authorize)
    return await user_utils.reset_time(username)


@app.post("/reset_password")
async def post_turn(request: Request):
    user = await auth_utils.get_user(AuthJWT(req=request))
    data = await request.json()
    if "password" not in data or "password" in data and bool(data["password"]) == False:
        raise HTTPException(status_code=409, detail="Not valid password")
    user.password = user_utils.get_password_hash(data["password"])
    await user.save()


otp_key = "otpsecret"
totp = pyotp.TOTP(base64.b32encode(otp_key.encode()))

@app.post('/login')
async def login(user: pydantic_models.AuthData, Authorize: AuthJWT = Depends()):
    try:
        u = await user_utils.authenticate_user(user.username, user.password)
        if u is None:
            raise HTTPException(status_code=409, detail="Bad username or password")
        print("OK")
        if u.isF2Aenabled:
            print(user.F2A)
            print("OOOOOOOOOOOOO")
            allowed = totp.verify(user.F2A)
            if not allowed:
                raise HTTPException(status_code=409, detail="Bad F2A")
    except Exception as e:
        print(type(e), e)
        raise HTTPException(status_code=401, detail=str(e))
    print("giving access token")
    access_token = await Authorize.create_access_token(subject=u.username)
    print("giving refresh token")
    refresh_token = await Authorize.create_refresh_token(subject=u.username)
    return {"access_token": access_token, "refresh_token": refresh_token}


@app.post("/otp_status")
async def set_otp_status(request: Request):
    user = await auth_utils.get_user(AuthJWT(req=request))
    user.isF2Aenabled = int(bool(int(request.query_params["value"])))
    await user.save()
    
@app.get("/otp_status")
async def get_otp_status(Authorize: AuthJWT = Depends()):
    user = await auth_utils.get_user(Authorize)
    return user.isF2Aenabled

@app.get("/otp")
async def get_otp(request: Request):
    user = await auth_utils.get_user(AuthJWT(req=request))
    return totp.provisioning_uri(name=user.uuid, issuer_name="Bot Panel")


@app.post('/refresh')
async def refresh(Authorize: AuthJWT = Depends()):
    return await auth_utils.refresh(Authorize)


@app.get("/users")
async def get_users(Authorize: AuthJWT = Depends()):
    await auth_utils.checkAdminPrivileges(Authorize)
    return await user_utils.get_users()


@app.post("/users")
async def post_users(request: pydantic_models.CreateUser, Authorize: AuthJWT = Depends()):
    await auth_utils.checkAdminPrivileges(Authorize)
    await user_utils.post_users(request)
    return True


@app.put("/users")
async def put_users(request: pydantic_models.EditUser, Authorize: AuthJWT = Depends()):
    await auth_utils.checkAdminPrivileges(Authorize)
    await user_utils.put_users(request)
    return True


@app.delete("/users")
async def delete_users(username: str, Authorize: AuthJWT = Depends()):
    await auth_utils.checkAdminPrivileges(Authorize)
    await user_utils.delete_users(username)


@app.get("/autotexts")
async def get_autotext(Authorize: AuthJWT = Depends()):
    await auth_utils.get_user(Authorize)
    return await autotext_utils.get_autotext()


@app.post("/autotexts")
async def post_autotext(request: pydantic_models.CreateAutotext, Authorize: AuthJWT = Depends()):
    await auth_utils.checkAdminPrivileges(Authorize)
    await autotext_utils.post_autotext(request)
    return True


@app.put("/autotexts")
async def put_autotext(request: pydantic_models.EditAutotext, Authorize: AuthJWT = Depends()):
    await auth_utils.checkAdminPrivileges(Authorize)
    await autotext_utils.put_autotext(request)
    return True


@app.delete("/autotexts")
async def delete_autotexts(id: int, Authorize: AuthJWT = Depends()):
    await auth_utils.checkAdminPrivileges(Authorize)
    await autotext_utils.delete_autotext(id)


@app.get("/tickets")
async def get_tickets(request: Request):
    try:
        Authorize = AuthJWT(req=request)
        user = await auth_utils.get_user(Authorize)
        temp = await tickets_utils.get_tickets(user)
        return temp
    except MissingTokenError as e:
        if "tg-bot-secret" in request.headers and request.headers["tg-bot-secret"] != "tg-bot-secret-123456":
            raise HTTPException(403)
        query_params = dict(request.query_params)
        if "client_username" in query_params:
            print("TEST")
            return [r.uu_id for r in await peewee_models.Ticket.select().where(
                peewee_models.Ticket.client_username == query_params["client_username"])]


#@app.post("/ticket")
#async def post_ticket(request: Request):
    #if request.headers["tg-bot-secret"] != "tg-bot-secret-123456":
        #raise HTTPException(403)
    #if "uuid" in request.query_params:
        #ticket = await peewee_models.Ticket.get_or_none()
        #ticket.status = None
        #await ticket.save()
    #raise HTTPException(409)


@app.post("/ticket")
async def post_ticket(request: Request):
    if request.headers["tg-bot-secret"] != "tg-bot-secret-123456":
        raise HTTPException(403)
    body = await request.json()
    await peewee_models.Ticket.create(**body, date_of_last_change=datetime.datetime.now())


@app.post("/new_message")
async def post_new_message(request: Request):
    from_operator = False
    try:
        await auth_utils.get_user(AuthJWT(req=request))
        from_operator = True
    except HTTPException as e:
        if request.headers["tg-bot-token"] != "tg-bot-secret-123456":
            raise HTTPException(403)


@app.get("/orders")
async def get_orders(Authorize: AuthJWT = Depends()):
    await auth_utils.get_user(Authorize)
    return await order_utils.get_orders()


@app.get("/order")
async def get_order(request: Request):
    if request.headers["tg-bot-secret"] != "tg-bot-secret-123456":
        raise HTTPException(403)
    orderID = request.query_params["orderID"]
    return await order_utils.get_order(orderID)


@app.post("/webhook/order")
async def post_order(request: pydantic_models.Order):
    return await order_utils.post_order(request)


@app.post("/webhook/update")  # Switched "/card" to "/update" as clien asked 
async def post_card(request: pydantic_models.Card):
    return await card_utils.post_card(request)


@app.get("/bots")
async def get_bots(Authorize: AuthJWT = Depends()):
    await auth_utils.checkAdminPrivileges(Authorize)
    return await bots_utils.get_bots()


@app.post("/bots")
async def post_bot(request: pydantic_models.CreateBot, Authorize: AuthJWT = Depends()):
    await auth_utils.checkAdminPrivileges(Authorize)
    await bots_utils.create_bot(name=request.name, token=request.token)


@app.delete("/bots")
async def delete_bot(request: Request):
    await auth_utils.checkAdminPrivileges(AuthJWT(req=request))
    await bots_utils.delete_bot(request.query_params["token"])


@app.post("/bot_start")
async def start_bot(request: Request):
    await auth_utils.checkAdminPrivileges(AuthJWT(req=request))
    await bots_utils.start_bot(request.query_params["token"])


@app.post("/bot_stop")
async def stop_bot(request: Request):
    await auth_utils.checkAdminPrivileges(AuthJWT(req=request))
    await bots_utils.stop_bot(request.query_params["token"])


@app.put("/bots")
async def put_bot(request: Request):
    await auth_utils.checkAdminPrivileges(AuthJWT(req=request))
    body = await request.json()
    await bots_utils.edit_bot(token=request.query_params["token"], name=body["name"], new_token=body["token"])

@app.put("/ticket_status")
async def put_ticket_status(request: Request):
    ticket = await peewee_models.Ticket.get_or_none(peewee_models.Ticket.uu_id == request.query_params["uu_id"])
    if ticket:
        ticket.status = request.query_params["value"]
        await ticket.save()

@app.put("/order_status")
async def put_order_status(request: Request):
    order = await peewee_models.Order.get_or_none(peewee_models.Order.uu_id == request.query_params["uu_id"])
    if order:
        order.status = request.query_params["value"]
        await order.save()

@app.get("/messages")
async def get_messages(request: Request):
    try:
        await auth_utils.get_user(AuthJWT(req=request))
        pos = int(request.headers.get("clen"))
        if pos < 0:
            raise HTTPException(422)
        if "uuid" not in request.headers.keys():
            raise HTTPException(422)
        res = [
            {
                "from_operator": m.from_operator,
                "text": m.text,
                "img": m.img,
                "timestamp": m.timestamp
            } for m in
            await peewee_models.Message.select().where(peewee_models.Message.uu_id == request.headers.get("uuid"))
        ]
        return JSONResponse(res[pos:])
    except MissingTokenError as e:
        if request.headers["tg-bot-secret"] != "tg-bot-secret-123456":
            raise HTTPException(403)
        res = []
        for message in await peewee_models.Message.select():
            if "uu_id" in request.query_params and message.uu_id != request.query_params["uu_id"]:
                continue
            if "from_operator" in request.query_params and message.from_operator != int(
                    request.query_params["from_operator"]):
                continue
            if "client_username" in request.query_params:
                t = str(message.uu_id)
                print(t)
                ticket = await peewee_models.Ticket.get_or_none(peewee_models.Ticket.uu_id == t)
                if ticket and ticket.client_username != request.query_params["client_username"]:
                    continue
            res.append(
                {
                    "from_operator": message.from_operator,
                    "text": message.text,
                    "img": message.img,
                    "timestamp": message.timestamp
                }
            )
        return JSONResponse(res)


@app.post("/message")
async def post_message(request: Request):
    from_operator = True
    try:
        await auth_utils.get_user(AuthJWT(req=request))
    except MissingTokenError as e:
        if request.headers["tg-bot-secret"] != "tg-bot-secret-123456":
            raise HTTPException(403)
        from_operator = False
    try:
        r = await request.json()
        await peewee_models.Message.create(uu_id=r["uuid"], from_operator=from_operator, text=r["text"],
                                           img=r["img"] if "img" in r else None)
        ticket = await peewee_models.Ticket.get_or_none(peewee_models.Ticket.uu_id == r["uuid"])
        if ticket:
            ticket.date_of_last_change = datetime.datetime.now()
            await ticket.save()
        if from_operator:
            user_id = int((await peewee_models.Ticket.get(peewee_models.Ticket.uu_id == r["uuid"])).client_username)
            print(user_id)
            # bot.operator_send_message(user_id, r["text"], r["uuid"])
    except HTTPException as e:
        raise e
    except BaseException as e:
        print(type(e), e)
        raise HTTPException(422)


@app.post("/client")
async def post_client(request: Request):
    if "tg-bot-secret" in request.headers and request.headers["tg-bot-secret"] != "tg-bot-secret-123456":
        raise HTTPException(403)
    try:
        body = await request.json()
        print(body)
        user = await peewee_models.Client.get_or_none(peewee_models.Client.user_id == body["user_id"])
        if not user:
            await peewee_models.Client.create(**body)
    except BaseException as e:
        print(e)
        raise HTTPException(400)


@app.get("/clients")
async def get_clients(Authorize: AuthJWT = Depends()):
    await auth_utils.checkAdminPrivileges(Authorize)
    return [
        {
            "displaybleName": client.first_name if client.last_name != "None" else f"{client.first_name} {client.last_name}",
            "username": client.username,
            "phoneNumber": client.phone_number,
            "user_id": client.user_id
        } for client in await peewee_models.Client.select()
    ]


@app.get("/tabs")
async def get_tabs(Authorize: AuthJWT = Depends()):
    user = await auth_utils.get_user(Authorize)
    if user.role == 0:
        return [
            {
                "id": "Tickets_tab",
                "buttonText": "Тикеты",
            },
            {
                "id": "Employees_tab",
                "buttonText": "Сотрудники",
            },
            {
                "id": "Clients_tab",
                "buttonText": "Клиенты",
            },
            {
                "id": "Bots_tab",
                "buttonText": "Боты",
            },
            {
                "id": "System_tab",
                "buttonText": "Система",
            }
        ]
    elif user.role == 1:
        return [
            {
                "id": "Tickets_tab",
                "buttonText": "Тикеты"
            },
            {
                "id": "System_tab",
                "buttonText": "Система"
            }
        ]
    elif user.role == 2:
        return [
            {
                "id": "Tickets_tab",
                "buttonText": "Тикеты"
            }
        ]
    else:
        return []
