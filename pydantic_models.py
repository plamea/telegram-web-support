from typing import Literal

from pydantic import BaseModel


class Settings(BaseModel):
    authjwt_secret_key: str = "secret"


class AuthData(BaseModel):
    username: str
    password: str
    F2A: str = None


class CreateAutotext(BaseModel):
    priority: int
    title: str
    message: str


class EditAutotext(BaseModel):
    id: int
    priority: int
    title: str
    message: str


class CreateUser(BaseModel):
    adminID: int | None = None
    displayableName: str
    username: str
    password: str
    role: int = 2


class EditUser(BaseModel):
    uuid: str
    adminID: int
    displayableName: str
    username: str
    password: str | None = None
    role: int


class Order(BaseModel):
    uu_id: str
    card_number: str
    masked_card_number: str
    amount: int
    source: int
    currency: Literal["RUB", "UAH", "KZT"]
    status: Literal["deleted", "waiting", "success", "success_error", "success_operator"]
    isP2PCard: bool
    create_time: str
    remove_time: str
    pay_time: str
    card_id: int | None


class Card(BaseModel):
    card_id: int
    note: str


class Ticket(BaseModel):
    ticket_uu_id: str
    order_uu_id: str
    client_username: str
    status: Literal["new", "in_work", "solved", "declined", "pending"]
    is_checked: bool
    is_last_answer_from_operator: bool
    date_of_request: str
    date_of_last_change: str


class CreateBot(BaseModel):
    name: str
    token: str


class EditBot(BaseModel):
    name: str
    token: str


class CreateTicket(BaseModel):
    uu_id: str
    username: str
    date_of_request: str
    date_of_last_change: str

class CreateClient(BaseModel):
    first_name: str
    last_name: str | None
    username: str | None
    phone_number: str | None
    user_id: str | None
