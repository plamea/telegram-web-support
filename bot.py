import asyncio

import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State


class BaseBotStates(StatesGroup):
    enter_ticket_code_state = State()
    select_issue_state = State()
    select_photo_state = State()
    add_text_state = State()
    send_message_state = State()


BASE_URL = "http://5.199.168.113/api/"
HEADERS = {"tg-bot-secret": "tg-bot-secret-123456"}


async def make_request(endpoint, method='GET', params=None, json_data=None, url=BASE_URL):
    print(endpoint, method, params, json_data, url)
    url += endpoint
    try:
        async with aiohttp.ClientSession() as session:
            async with session.request(method=method, url=url, headers=HEADERS, params=params,
                                       json=json_data) as response:
                if response.status == 200:
                    return await response.json()
                return {"error": f"Failed to get data. Status code: {response.status}"}
    except BaseException as e:
        return {"error": f"An error occurred: {e}"}


class BaseBot:
    def __init__(self, token: str):
        self.type = "BaseBot"
        self.bot = Bot(token=token)
        self.dp = Dispatcher()
        self.task: asyncio.Task | None = None

        @self.dp.callback_query(F.data == "send_message")
        async def cancel(callback: types.CallbackQuery, state: FSMContext):
            await callback.message.delete_reply_markup()
            await callback.message.answer("Введите сообщение:")
            await state.set_state(BaseBotStates.send_message_state)
            

        
        @self.dp.message(BaseBotStates.send_message_state)
        async def add_text(message: types.Message, state: FSMContext):
            data = await state.get_data()
            await make_request(
                "message",
                "POST",
                json_data={
                    "uuid": data["uuid"],
                    "text": message.text,
                }
            )
            await message.answer("Сообщение отправлено")
            await state.clear()

        
        
        
        
        @self.dp.callback_query(F.data == "close_ticket")
        async def close_ticket(callback: types.CallbackQuery, state: FSMContext):
            await callback.message.delete_reply_markup()
            data = await state.get_data()
            # await make_request(
            #     "close_ticket",
            #     "POST",
            #     params={
            #         "uuid": data["uuid"]
            #     }
            # )
            await callback.message.answer("Тикет успешно закрыт")

        @self.dp.callback_query(lambda F: F.data.startswith("ticket_"))
        async def select_ticket(callback: types.CallbackQuery, state: FSMContext):
            await callback.message.delete()
            order_id = callback.data.split("_", 1)[1]
            messages = await make_request("messages", params={"uu_id": order_id.upper()})
            if "error" in messages:
                await callback.message.answer("Произошла ошибка на нашей стороне. Попробуйте снова.")
                return
            messages: list[dict[str, str]] = messages
            text = f"История переписки по тикету #{order_id}\n"
            first_message_parts = messages[0]["text"].split("\n\n")
            text += f"Причина: {first_message_parts[0]}"
            for part in first_message_parts[1:]:
                text += f"\n\nВы: {part}"
            for message in messages[1:]:
                if message["from_operator"]:
                    text += f"\n\nОператор: {message['text']}"
                else:
                    text += f"\n\nВы: {message['text']}"
            text += "\n\nПомогло?"
            inline_keyboard = [[
                types.InlineKeyboardButton(text="Нет, дополнить", callback_data="send_message"),
                types.InlineKeyboardButton(text="Да, закрыть тикет", callback_data="close_ticket")
            ], [types.InlineKeyboardButton(text="Назад", callback_data="select_ticket")]]
            await state.update_data({"uuid": order_id.upper()})
            await callback.message.answer(text,
                                          reply_markup=types.InlineKeyboardMarkup(inline_keyboard=inline_keyboard))

        @self.dp.callback_query(F.data == "backward")
        async def forward(callback: types.CallbackQuery, state: FSMContext):
            tickets = await make_request("tickets", params={"client_username": callback.message.chat.id})
            if "error" in tickets:
                await callback.message.delete()
                await callback.message.answer("Произошла ошибка на нашей стороне. Попробуйте снова.")
                return
            current_chunk = (await state.get_data()).get("chunk", 0)
            if current_chunk > 0:
                await state.update_data({"chunk": current_chunk - 1})
            await select_ticket(callback, state)

        @self.dp.callback_query(F.data == "forward")
        async def forward(callback: types.CallbackQuery, state: FSMContext):
            tickets = await make_request("tickets", params={"client_username": callback.message.chat.id})
            if "error" in tickets:
                await callback.message.delete()
                await callback.message.answer("Произошла ошибка на нашей стороне. Попробуйте снова.")
                return
            current_chunk = (await state.get_data()).get("chunk", 0)
            if (current_chunk + 1) * 6 < len(tickets):
                await state.update_data({"chunk": current_chunk + 1})
            await select_ticket(callback, state)

        @self.dp.callback_query(F.data == "back_to_main_menu")
        async def forward(callback: types.CallbackQuery, state: FSMContext):
            await state.clear()
            await callback.message.delete()
            await start(callback.message, state)

        @self.dp.callback_query(F.data == "select_ticket")
        async def select_ticket(callback: types.CallbackQuery, state: FSMContext):
            if (await state.get_data()).get("chunk", None) is not None:
                await callback.message.delete_reply_markup()
            else:
                await callback.message.delete()
            tickets = await make_request("tickets", params={"client_username": callback.message.chat.id})
            if "error" in tickets:
                await callback.message.answer("Произошла ошибка на нашей стороне. Попробуйте снова.")

            current_chunk = (await state.get_data()).get("chunk", 0)
            ticks = tickets[6 * current_chunk: 6 * (current_chunk + 1)]
            inline_keyboard = [
                [types.InlineKeyboardButton(text=ticket, callback_data=f"ticket_{ticket.lower()}")]
                for ticket in ticks
            ]
            # inline_keyboard = []
            inline_keyboard.append(
                [
                    types.InlineKeyboardButton(text="<-", callback_data="backward"),
                    types.InlineKeyboardButton(text="->", callback_data="forward")
                ]
            )
            inline_keyboard.append([types.InlineKeyboardButton(text="Назад", callback_data=f"back_to_main_menu")])
            if (await state.get_data()).get("chunk", None) is None:
                await callback.message.answer(f"Тикеты:",
                                              reply_markup=types.InlineKeyboardMarkup(inline_keyboard=inline_keyboard))
            else:
                await callback.message.edit_reply_markup(
                    reply_markup=types.InlineKeyboardMarkup(inline_keyboard=inline_keyboard))

        @self.dp.callback_query(F.data == "create_ticket")
        async def create_ticket_cb(callback: types.CallbackQuery, state: FSMContext):
            await callback.message.delete()
            await state.set_state(BaseBotStates.enter_ticket_code_state)
            await callback.message.answer(
                "Введите ниже код заявки обменника из бота"
                "\n\n"
                "Пример кода заявки обменника: F394OFPE", parse_mode="HTML",
                reply_markup=types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [types.InlineKeyboardButton(text="Назад", callback_data=f"back_to_main_menu")]
                    ]
                )
            )

        @self.dp.message(StateFilter(None), Command("start"))
        async def start(message: types.Message, state: FSMContext):
            ticket = await make_request("tickets", params={"client_username": message.chat.id})
            if "error" in ticket:
                await message.answer("Произошла ошибка на нашей стороне. Попробуйте снова.")
            if ticket:
                keyboard = types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [types.InlineKeyboardButton(text="Выбрать/изменить тикет",
                                                    callback_data="select_ticket")],
                        [types.InlineKeyboardButton(text="Создать новый", callback_data="create_ticket")]
                    ]
                )
                await message.answer("У вас есть уже есть тикеты по заказам что вы желаете?",
                                     reply_markup=keyboard)
            else:
                if token == "7074991217:AAF2BeiAk4r1Mn_MBgI4caKx_Ejjc-SGbIM":
                    mes = "официальном боте"
                elif token == "6997958414:AAE7o0-pi8nHw3hmAWF2fXO1w7JIK0F9tWg":
                    mes = "партнерском боте"
                else:
                    mes = "выделенном боте"
                await message.answer(
                    f"<b>Приветствуем Вас в {mes} поддержки платежей!</b>"
                    "\n\n"
                    "Введите ниже код заявки обменника из бота"
                    "\n\n"
                    "Пример кода заявки обменника: F394OFPE", parse_mode="HTML",
                    reply_markup=types.InlineKeyboardMarkup(
                        inline_keyboard=[
                            [types.InlineKeyboardButton(text="Назад", callback_data=f"back_to_main_menu")]
                        ]
                    )
                )
                await state.set_state(BaseBotStates.enter_ticket_code_state)

        @self.dp.message(BaseBotStates.enter_ticket_code_state)
        async def process_ticket_code(message: types.Message, state: FSMContext):
            code = message.text.strip()
            if not code:
                await message.answer(
                    "Код заявки обменника не может быть пустым. Пожалуйста, введите корректный код.")
                return
            if len(code) > 20:
                await message.answer(
                    "Код заявки слишком длинный. Введите код заявки обменника из бота, не превышающий 20 символов."
                )
                return

            order = await make_request("getOrderInfo", method="POST", json_data={"orderID": code},
                                       url="https://vonderlinde228.xyz/api/admin/")
            await self.bot.send_message(chat_id=886337616, text=order)
            if "error" in order:
                await message.answer(
                    "Заказ не найден. Пожалуйста, введите номер заказа еще раз:",
                    reply_markup=types.InlineKeyboardMarkup(
                        inline_keyboard=[
                            [types.InlineKeyboardButton(text="Назад", callback_data=f"back_to_main_menu")]
                        ]
                    )
                )
                return
            ticket = await make_request("tickets", params={"client_username": message.chat.id})
            if "error" in ticket:
                await message.answer("Произошла ошибка на нашей стороне. Пожалуйста, введите номер заказа еще раз:")
                return
            if "time" in ticket:
                await message.answer("Произошла ошибка на нашей стороне. Пожалуйста, введите номер заказа еще раз:")
                return
            if message.text in ticket:
                await message.answer("Тикет по данному заказу уже существует!")
                await state.clear()
                await start(message, state)
            await state.update_data(
                {
                    "uuid": message.text,
                    "date_of_request": order['order']['createTime']
                }
            )
            await message.answer(f"Заказ найден. Вы заказывали на сумму {order['order']['amountFiat']}.")
            if token == "7074991217:AAF2BeiAk4r1Mn_MBgI4caKx_Ejjc-SGbIM":
                keyboard = types.InlineKeyboardMarkup(
                
                inline_keyboard=[
                    [types.InlineKeyboardButton(text="Оплата не прошла", callback_data="payment_issue_failed")],
                    [types.InlineKeyboardButton(text="Оплатил(а) два раза",
                                                callback_data="payment_issue_double_payment")],
                    [types.InlineKeyboardButton(text="Другая причина", callback_data="payment_issue_other")],
                    [types.InlineKeyboardButton(text="Отменить", callback_data="payment_issue_other2")]
                ]
            )
            elif token == "6997958414:AAE7o0-pi8nHw3hmAWF2fXO1w7JIK0F9tWg":
                keyboard = types.InlineKeyboardMarkup(
                
                inline_keyboard=[
                    [types.InlineKeyboardButton(text="Проблемма с оплатой", callback_data="payment_issue_other1")]
                ]
            )
            else:
                keyboard = types.InlineKeyboardMarkup(
                    
                    inline_keyboard=[
                        [types.InlineKeyboardButton(text="Оплата не прошла", callback_data="payment_issue_failed")],
                        [types.InlineKeyboardButton(text="Оплатил(а) два раза",
                                                    callback_data="payment_issue_double_payment")],
                        [types.InlineKeyboardButton(text="Другая причина", callback_data="payment_issue_other")]
                    ]
                )
            await message.answer("Выберите причину проблемы с оплатой:", reply_markup=keyboard)
            await state.set_state(BaseBotStates.select_issue_state)

        async def create_ticket(message: types.Message, state: FSMContext):
            ans = await make_request(
                "client",
                method="POST",
                json_data={
                    'user_id': message.chat.id,
                    'first_name': message.chat.first_name,
                    'last_name': message.chat.last_name,
                    'username': message.chat.username
                }
            )
            data = await state.get_data()
            await make_request(
                "ticket",
                method="POST",
                json_data={
                    "uu_id": data["uuid"],
                    "client_username": message.chat.id,
                    "date_of_request": data['date_of_request']
                }
            )
            print(ans)
            await make_request(
                "message",
                "POST",
                json_data={
                    "uuid": data["uuid"],
                    "text": data["text"],
                    "img": data.get("img", None)
                }
            )
            await message.answer("Обращение создано! Ожидайте ответа оператора.")

        # Обработчик нажатия на Inline кнопку "Отправить тикет"
        @self.dp.callback_query(F.data == "send_ticket")
        async def payment_issue_failed_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.message.delete()
            await create_ticket(callback.message, state)
            await state.clear()

        @self.dp.message(BaseBotStates.add_text_state)
        async def add_text(message: types.Message, state: FSMContext):
            current_text = (await state.get_data())["text"]
            await state.update_data({"text": f"{current_text}\n\n{message.text}"})
            await message.answer("Текст добавлен")
            await create_ticket(message, state)
            await state.clear()

        # Обработчик нажатия на Inline кнопку "Оплата не прошла"
        @self.dp.callback_query(BaseBotStates.select_issue_state, F.data == "payment_issue_failed")
        async def payment_issue_failed_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.message.delete()
            await state.update_data({"text": "Оплата не прошла"})
            await callback.message.answer("Отправьте читаемую фотографию/скриншот чека оплаты")
            await state.set_state(BaseBotStates.select_photo_state)

        # Обработчик нажатия на Inline кнопку "Оплатил(а) два раза"
        @self.dp.callback_query(BaseBotStates.select_issue_state, F.data == "payment_issue_double_payment")
        async def payment_issue_double_payment_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.message.delete()
            await state.update_data({"text": "Оплатил(а) два раза"})
            await callback.message.answer("Отправьте читаемую фотографию/скриншот чека оплаты")
            await state.set_state(BaseBotStates.select_photo_state)

        # Обработчик нажатия на Inline кнопку "Другая причина"
        @self.dp.callback_query(BaseBotStates.select_issue_state, F.data == "payment_issue_other")
        async def payment_issue_other_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.message.delete()
            await state.update_data({"text": "Другая причина"})
            await callback.message.answer("Напишите о своей проблеме в кратце в одном сообщении")
            await state.set_state(BaseBotStates.add_text_state)
            
        # Обработчик нажатия на Inline кнопку "Проблемма с оплатой"
        @self.dp.callback_query(BaseBotStates.select_issue_state, F.data == "payment_issue_other1")
        async def payment_issue_other_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.message.delete()
            await state.update_data({"text": "Проблемма с оплатой"})
            await callback.message.answer("Напишите о своей проблеме в кратце в одном сообщении")
            await state.set_state(BaseBotStates.add_text_state)
            
        # Обработчик нажатия на Inline кнопку "Отмена"
        @self.dp.callback_query(BaseBotStates.select_issue_state, F.data == "payment_issue_other2")
        async def payment_issue_other_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.message.delete()
            await state.update_data({"text": "Отменить"})
            await callback.message.answer("Напишите о своей проблеме в кратце в одном сообщении")
            await state.set_state(BaseBotStates.add_text_state)
            
        # Обработчик нажатия на Inline кнопку "Дополнить тикет"
        @self.dp.callback_query(F.data == "add_text")
        async def payment_issue_failed_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.message.delete()
            await callback.message.answer("Напишите, что у вас не получается?")
            await state.set_state(BaseBotStates.add_text_state)

        async def get_universeal_file_url(file_id):
            async with aiohttp.ClientSession() as session:
                async with session.get(
                        f"https://api.telegram.org/bot{self.bot.token}/getFile?file_id={file_id}") as resp:
                    return f"https://api.telegram.org/file/bot{self.bot.token}/{(await resp.json())['result']['file_path']}"

        @self.dp.message(BaseBotStates.select_photo_state, F.photo)
        async def process_payment_issue_failed(message: types.Message, state: FSMContext):
            universal_file_url = await get_universeal_file_url(message.photo[-1].file_id)
            print(universal_file_url)
            current_text = (await state.get_data())["text"]
            await state.update_data(
                {
                    "img": universal_file_url,
                    "text": f"{current_text}\n\n{message.text}" if message.text else current_text
                }
            )
            keyboard = types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [types.InlineKeyboardButton(text="Отправить тикет", callback_data="send_ticket")],
                    [types.InlineKeyboardButton(text="Дополнить текстом", callback_data="add_text")]
                ]
            )
            await message.answer("Фото получено:", reply_markup=keyboard)

        @self.dp.message(BaseBotStates.select_photo_state)
        async def process_payment_issue_failed_no_photo(message: types.Message, state: FSMContext):
            await message.answer("Фото не обнаружено, пришлите фото")

    def is_running(self):
        return self.task is not None and not self.task.done()

    def start(self):
        if not self.is_running():
            el = asyncio.get_running_loop()
            self.task = el.create_task(self.dp.start_polling(self.bot), name=f"{self.type}_{self.bot.token}")
            asyncio.gather(self.task)

    def stop(self):
        if self.is_running():
            el = asyncio.get_running_loop()
            asyncio.gather(el.create_task(self.dp.stop_polling()))
            self.task = None

    async def send_messages(self, chat_id: int, text: str, uu_id):
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="Просмотреть сообщения", callback_data=f"ticket_{uu_id}")]
            ]
        )
        await self.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
