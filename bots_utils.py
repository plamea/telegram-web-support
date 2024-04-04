import bot as bot_module
import peewee_models

running_bots: dict[str, bot_module.BaseBot] = {}


async def create_bot(name: str, token: str):
    try:
        await peewee_models.Bot.create(name=name, token=token)
    except BaseException as e:
        print(e)


async def start_bot(token: str) -> bool:
    if running_bots.get(token, None) is None:
        running_bots[token] = bot_module.BaseBot(token)
        running_bots[token].start()


async def stop_bot(token: str) -> bool:
    bot = running_bots.get(token, None)
    if bot is not None:
        bot.stop()
        running_bots.pop(token)


async def delete_bot(token: str) -> bool:
    await stop_bot(token)
    bot = await peewee_models.Bot.get_or_none(peewee_models.Bot.token == token)
    if bot is not None:
        await bot.delete_instance()


async def edit_bot(token, name, new_token):
    bot = await peewee_models.Bot.get_or_none(peewee_models.Bot.token == token)
    if bot is None:
        return

    bot_is_running = token in running_bots
    if bot_is_running:
        await stop_bot(token)
    try:
        bot.name = name
        bot.token = new_token
        await bot.save()
    except BaseException as e:
        print(e)
    if bot_is_running:
        await start_bot(new_token)


async def get_bots():
    res = []
    for bot in await peewee_models.Bot.select():
        res.append(
            {
                "name": bot.name,
                "token": bot.token,
                "is_online": True if bot.token in running_bots else False
            }
        )
    return res
