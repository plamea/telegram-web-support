import asyncio

from peewee_aio import AIOModel, Manager, fields
import datetime
#url = "sqlite:///C:/Users/Plamea/Desktop/sait/Back/database.db"
url = f"sqlite:///database.db"
manager = Manager(url)



@manager.register
class User(AIOModel):
    uuid = fields.CharField(unique=True)
    adminID = fields.IntegerField(unique=True)
    displayableName = fields.CharField(unique=True)
    username = fields.CharField(unique=True)
    password = fields.CharField()
    lastSeen = fields.IntegerField(default=0)
    turn = fields.BooleanField(default=False)
    time = fields.IntegerField(default=0)
    role = fields.IntegerField(default=2)
    isF2Aenabled = fields.IntegerField(default=0)

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "adminID": self.adminID,
            "username": self.username,
            "displayableName": self.displayableName,
            #"lastSeen": self.lastSeen,
            "turn": self.turn,
            "time": self.time,
            "role": self.role
        }


@manager.register
class History(AIOModel):
    uuid = fields.IntegerField()
    event_type = fields.IntegerField()
    time = fields.IntegerField()


@manager.register
class Autotext(AIOModel):
    priority = fields.IntegerField()
    title = fields.TextField()
    message = fields.TextField()

    def to_dict(self):
        return {
            "id": self.get_id(),
            "priority": self.priority,
            "title": self.title,
            "message": self.message
        }


@manager.register
class UsedToken(AIOModel):
    token = fields.TextField()

@manager.register
class Bot(AIOModel):
    name = fields.CharField(unique=True)
    token = fields.CharField(unique=True)


@manager.register
class Order(AIOModel):
    uu_id = fields.CharField(unique=True)
    card_number = fields.CharField()
    masked_card_number = fields.CharField()
    amount = fields.IntegerField()
    source = fields.IntegerField()
    currency = fields.CharField()
    status = fields.CharField()
    isP2PCard = fields.IntegerField()
    create_time = fields.CharField()
    remove_time = fields.CharField()
    pay_time = fields.CharField()
    card_id = fields.IntegerField(null=True)

    def to_dict(self):
        return {
            "uu_id": self.uu_id,
            "card_number": self.card_number,
            "masked_card_number": self.masked_card_number,
            "amount": self.amount,
            "source": self.source,
            "currency": self.currency,
            "status": self.status,
            "isP2PCard": self.isP2PCard,
            "create_time": self.create_time,
            "remove_time": self.remove_time,
            "pay_time": self.pay_time,
            "card_id": self.card_id
        }


# В файле peewee_models.py

async def get_user_role(username):
    async with manager:
        async with manager.connection():
            user = await User.get_or_none(username=username)
            if user:
                return user.role
            else:
                return None



@manager.register
class Card(AIOModel):
    card_id = fields.IntegerField(unique=True)
    note = fields.CharField()

    def to_dict(self):
        return {
            "card_id": self.card_id,
            "note": self.note
        }


@manager.register
class Ticket(AIOModel):
    uu_id = fields.CharField(unique=True)
    client_username = fields.CharField()
    status = fields.CharField(default="new")
    is_checked = fields.BooleanField(default=False)
    is_last_answer_from_operator = fields.BooleanField(default=False)
    operator = fields.CharField(null=True)
    date_of_request = fields.CharField()
    date_of_last_change = fields.CharField()

    def to_dict(self):
        return {
            "uu_id": self.uu_id,
            "status": self.status,
            "date_of_request": self.date_of_request,
            "date_of_last_change": self.date_of_last_change
        }


@manager.register
class Message(AIOModel):
    uu_id = fields.CharField()
    from_operator = fields.BooleanField(default=False)
    text = fields.TextField(null=True)
    img = fields.TextField(null=True)
    timestamp = fields.IntegerField(default=lambda:int(datetime.datetime.now().timestamp()))

@manager.register
class Client(AIOModel):
    first_name = fields.CharField()
    last_name = fields.CharField(null=True, default=None)
    username = fields.CharField(null=True, default=None)
    phone_number = fields.CharField(null=True, default=None)
    user_id = fields.CharField(unique=True)


async def init_db():
    async with manager:
        async with manager.connection():
            await User.create_table()
            await History.create_table()
            await UsedToken.create_table()
            await Autotext.create_table()
            await Order.create_table()
            await Card.create_table()
            await Ticket.create_table()
            await Message.create_table()
            await Client.create_table()
            await Bot.create_table()


if __name__ == "__main__":
    el = asyncio.get_event_loop()
    el.run_until_complete(init_db())
