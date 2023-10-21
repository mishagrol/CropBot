from functools import partial
import logging
import json
import time
from typing import Union
from aiogram import Bot, Dispatcher, types

from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.utils import executor
from aiogram.contrib.middlewares.logging import LoggingMiddleware

# from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode, Message
from aiogram.types import (
    ReplyKeyboardRemove,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.types.message import ContentType

# from aiogram.utils import executor
import datetime
import os
import subprocess
from db import Database
from concurrent.futures.process import ProcessPoolExecutor
import uuid
import asyncio
import keyboards as kb
import aiogram.utils.markdown as md
from collections import defaultdict


from weather import AwsNasaPower, AWS_WOFOST
from bot_crop_model import Irrigation

aws = AwsNasaPower()

# from importlib import reload
# logging.shutdown()
# reload(logging)

with open("/home/token.json", "r") as file:
    BOT_TOKEN = json.load(file)["bot_token"]

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
# For example use simple MemoryStorage for Dispatcher.
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
# dp.middleware.setup(LoggingMiddleware())
db = Database()
crop_names = json.load(open("/home/src/utils_model/cultures.json", "r"))["cultures"]
crop_names_en = json.load(open("/home/src/utils_model/cultures_en.json", "r"))[
    "cultures"
]
ru_en_dict = json.load(open("/home/src/utils_model/ru_en_dict.json", "r"))
# dict to save chat_id and selected language of users
language = defaultdict(lambda: "EN")

# States
class Form(StatesGroup):
    main = State()
    add_field_name = State()  # Will be represented in storage as 'Form:name'
    add_field_location = State()  # Will be represented in storage as 'Form:age'
    add_field_crop_name = State()
    add_field_crop_start = State()
    add_field_crop_end = State()
    field_list = State()
    field_main = State()
    add_irrigation = State()
    add_npk = State()
    del_irrigation = State()
    del_npk = State()
    calculating = State()
    user_language = State()


async def log_message(
    data: Union[types.Message, types.CallbackQuery], state: FSMContext, extra_message=""
):
    cur_state = await state.get_state()
    if hasattr(data, "text"):
        logging.info(f"{data.chat.id} @ {cur_state}: {data.text}\n{extra_message}")
    elif hasattr(data, "message"):
        logging.info(
            f"{data.message.chat.id} @ {cur_state}: {data.data}\n{extra_message}"
        )


# Handle /cancel command
@dp.message_handler(state="*", commands="cancel")
async def cancel_handler(message: types.Message, state: FSMContext):
    await log_message(message, state)
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.finish()
    await message.reply(
        ru_en_dict["Отменено, введите /start"][language.get(message.chat.id, "EN")],
        reply_markup=types.ReplyKeyboardRemove(),
    )


# Handle /fields command
@dp.message_handler(state="*", commands="fields")
async def cmd_fields(message: types.Message, state: FSMContext):
    await log_message(message, state)
    lang = "EN"
    all_fields = await db.get_user_fields_irrs_npks(message.chat.id)
    field_names = [f.name for f, _, _ in all_fields]
    await message.reply(ru_en_dict["Известные поля"][lang], field_names)


@dp.message_handler(commands="start", state=None)
async def cmd_start(message: types.Message, state: FSMContext):
    logging.info("Start")
    await log_message(message, state)
    is_exists = await db.get_user(message.chat.id)
    if is_exists:
        # Load all data from DB
        async with state.proxy() as data:
            data["fields"] = await db.get_user_field_dicts(message.chat.id)
            logging.info(data["fields"])
    else:
        await db.new_user(message.chat.id, message.from_user.username)
        async with state.proxy() as data:
            if "fields" not in data:
                data["fields"] = {}

    logging.info("to state")
    await Form.main.set()
    lang = "EN"
    # temp_kb_inline = {"RU": kb.inline_main_kb, "EN": kb.inline_main_kb_en}
    menu = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Add field"), KeyboardButton(text="Select field")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await message.reply(
        "".join(
            [
                ru_en_dict["Здравствуйте,"][lang],
                message.from_user.first_name,
                "\n",
                ru_en_dict["Выберите действие:"][lang],
            ]
        ),
        reply_markup=menu,
    )


# Handle choose/edit fields dialoque
@dp.message_handler(
    lambda message: message.text in ["Add field", "Select field"], state=Form.main
)
async def process_callback_main(message: types.Message, state: FSMContext):

    await log_message(message, state)
    lang = language.get(message.chat.id, "EN")
    # await bot.edit_message_reply_markup(
    #     message.chat.id,
    #     message.message_id,
    #     reply_markup=None,
    # )
    user_id = message.chat.id
    if message.text == "Add field":
        await Form.add_field_name.set()
        await bot.send_message(
            message.from_user.id,
            ru_en_dict["Введите название поля:"][lang],
            reply_markup=types.ReplyKeyboardRemove(),
        )
    elif message.text == "Select field":
        all_fields = await db.get_user_fields(message.chat.id)
        if len(all_fields) == 0:
            await Form.main.set()

            temp_kb_main = {
                "RU": kb.inline_main_edit_kb,
                "EN": kb.inline_main_edit_kb_en,
            }

            await bot.send_message(
                message.from_user.id,
                ru_en_dict["У вас еще нет полей, добавьте с помощью кнопки ниже:"][
                    lang
                ],
                reply_markup=temp_kb_main[lang],
            )
        else:
            await Form.field_list.set()
            fields_btns = [
                InlineKeyboardButton(field.name, callback_data=f"field_{field.id}")
                for field in all_fields
            ]
            inline_main_edit_kb1 = InlineKeyboardMarkup().add(*fields_btns)
            await bot.send_message(
                message.from_user.id,
                ru_en_dict["Выберите поле для редактирования:"][lang],
                reply_markup=inline_main_edit_kb1,
            )


# Handle choosing fields dialoque
@dp.callback_query_handler(lambda callback_query: True, state=Form.field_list)
async def process_callback_main_field_list(
    callback_query: types.CallbackQuery, state: FSMContext
):

    await log_message(callback_query, state)
    lang = language.get(callback_query.message.chat.id, "EN")
    await bot.edit_message_reply_markup(
        callback_query.message.chat.id,
        callback_query.message.message_id,
        reply_markup=None,
    )
    if callback_query.data[:5] == "field":
        await Form.field_main.set()
        async with state.proxy() as data:
            data["current_field"] = callback_query.data.split("_")[1]
            await Form.field_main.set()

            temp_info = {
                "RU": kb.print_field_info(data["fields"][data["current_field"]]),
                "EN": kb.print_field_info_en(data["fields"][data["current_field"]]),
            }

            temp_keyboard = {
                "RU": kb.inline_main_field_kb,
                "EN": kb.inline_main_field_kb_en,
            }

            await bot.send_message(
                callback_query.from_user.id,
                temp_info[lang],
                reply_markup=temp_keyboard[lang],
                parse_mode=ParseMode.MARKDOWN,
            )


# Handle adding fields dialoque
@dp.message_handler(state=Form.add_field_name)
async def process_name(message: types.Message, state: FSMContext):
    await log_message(message, state)
    lang = "EN"
    async with state.proxy() as data:
        field_id = str(uuid.uuid4())
        data["current_field"] = field_id
        data["fields"][field_id] = {"name": message.text}

        # temp_geo_example_text = {
        #     "RU": kb.geo_example_text,
        #     "EN": kb.geo_example_text_en,
        # }

        await Form.add_field_location.set()
        await message.reply(
            ru_en_dict["Создано поле"][lang]
            + f" **{data['fields'][field_id]['name']}** "
            + kb.geo_example_text_en,
            reply_markup=types.ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN,
        )


def check_get_location(message):
    try:
        loc = message.text.split(", ")
        return True, [float(loc[0]), float(loc[1])]
    except:
        if message.location:
            return True, [message.location.latitude, message.location.longitude]
        else:
            return False, None


# Handle coordinates
@dp.message_handler(
    lambda message: check_get_location(message)[0],
    content_types=[ContentType.TEXT, ContentType.LOCATION],
    state=Form.add_field_location,
)
async def process_location(message: types.location, state: FSMContext):  # type: ignore

    lang = "EN"
    msg = message
    logging.info(msg)
    await Form.add_field_crop_name.set()
    async with state.proxy() as data:
        (
            data["fields"][data["current_field"]]["latitude"],
            data["fields"][data["current_field"]]["longitude"],
        ) = check_get_location(message)[
            1
        ]  # type: ignore
    dict_for_crops = {"RU": crop_names, "EN": crop_names_en}
    markup = ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add(*dict_for_crops[lang])
    await message.reply(ru_en_dict["Что растет?"][lang], reply_markup=markup)  # type: ignore


# Handle invalid coordinates
@dp.message_handler(
    lambda message: not check_get_location(message)[0], state=Form.add_field_location
)
async def process_location_invalid(message: types.Message, state: FSMContext):

    lang = "EN"
    temp_keyboard = {"RU": kb.back_markup, "EN": kb.back_markup_en}
    temp_geo_example_text = {"RU": kb.geo_example_text, "EN": kb.geo_example_text_en}

    return await message.reply(
        temp_geo_example_text[lang],
        reply_markup=temp_keyboard[lang],
        parse_mode=ParseMode.MARKDOWN,
    )


# Handle crop name
@dp.message_handler(
    lambda message: message.text in crop_names + crop_names_en,
    state=Form.add_field_crop_name,
)
async def process_crop_name(message: types.Message, state: FSMContext):

    lang = "EN"
    await Form.add_field_crop_start.set()
    async with state.proxy() as data:
        data["fields"][data["current_field"]]["crop_name"] = message.text
        markup = types.ReplyKeyboardRemove()
        await message.reply(
            ru_en_dict["Введите дату посева в формате день.месяц, 12.04"][lang],
            reply_markup=markup,
        )


# Handle invalid crop name
@dp.message_handler(
    lambda message: message.text not in crop_names + crop_names_en,
    state=Form.add_field_crop_name,
)
async def process_crop_name_invalid(message: types.Message, state: FSMContext):
    await log_message(message, state)
    lang = "EN"
    return await message.reply(ru_en_dict["Выберите культуру на клавиатуре"][lang])


def check_date_format(message):
    date_format = "%d.%m.%Y"
    try:
        datetime.datetime.strptime(message.text + ".2023", date_format).strftime(
            "%Y-%m-%d"
        )
        return True, datetime.datetime.strptime(message.text + ".2023", date_format)
    except:
        return False, None


# Handle crop start date (seeding)
@dp.message_handler(
    lambda message: check_date_format(message)[0], state=Form.add_field_crop_start
)
async def process_crop_start(message: types.Message, state: FSMContext):
    await log_message(message, state)
    lang = "EN"
    await Form.add_field_crop_end.set()
    async with state.proxy() as data:
        data["fields"][data["current_field"]]["crop_start"] = check_date_format(
            message
        )[1]
        await message.reply(
            ru_en_dict["Введите дату сборa урожая в формате день.месяц, 30.09"][lang]
        )


# Handle invalid crop start date (seeding)
@dp.message_handler(
    lambda message: not check_date_format(message)[0], state=Form.add_field_crop_start
)
async def process_crop_start_invalid(message: types.Message, state: FSMContext):
    await log_message(message, state)
    lang = "EN"
    return await message.reply(
        ru_en_dict["Введите дату посева в формате день.месяц, 12.04"][lang]
    )


# Handle crop end date (harvesting)
@dp.message_handler(
    lambda message: check_date_format(message)[0], state=Form.add_field_crop_end
)
async def process_crop_end(message: types.Message, state: FSMContext):
    await log_message(message, state)
    logging.info("We are in main menu")
    lang = "EN"
    async with state.proxy() as data:
        if (
            check_date_format(message)[1].date()  # type: ignore
            <= data["fields"][data["current_field"]]["crop_start"].date()
        ):
            await message.reply(
                ru_en_dict["Сбор урожая должен быть позже, чем посев"][lang],
                reply_markup=types.ReplyKeyboardRemove(),
            )
            return

        data["fields"][data["current_field"]]["crop_end"] = check_date_format(message)[
            1
        ]
        data["fields"][data["current_field"]]["irrigation"] = []
        data["fields"][data["current_field"]]["npk"] = []
        agro_dict = data["fields"][data["current_field"]]
        await db.add_field(
            data["current_field"],
            agro_dict["name"],
            message.chat.id,
            agro_dict["latitude"],
            agro_dict["longitude"],
            agro_dict["crop_start"],
            agro_dict["crop_end"],
            agro_dict["crop_name"],
        )
        data["fields"] = await db.get_user_field_dicts(message.chat.id)

        temp_keyboard = {
            "RU": kb.inline_main_field_kb,
            "EN": kb.inline_main_field_kb_en,
        }
        temp_info = {
            "RU": kb.print_field_info(data["fields"][data["current_field"]]),
            "EN": kb.print_field_info_en(data["fields"][data["current_field"]]),
        }

        inline_main_field_btns_en = [
            KeyboardButton("Add irrigation"),
            KeyboardButton("Add fertilization"),
            KeyboardButton("Remove irrigation"),
            KeyboardButton("Remove fertilization"),
            KeyboardButton("Remove field"),
            KeyboardButton("Back to select field"),
            KeyboardButton("COMPUTE"),
        ]
        # inline_main_field_kb_en = ReplyKeyboardMarkup(row_width=2).add(*inline_main_field_btns_en)
    # menu = ReplyKeyboardMarkup(
    #             keyboard=[KeyboardButton('Add irrigation' ),
    #                         KeyboardButton('Add fertilization'),
    #                         KeyboardButton('Remove irrigation'),
    #                         KeyboardButton('Remove fertilization'),
    #                         KeyboardButton('Remove field'),
    #                         KeyboardButton('Back to select field'),
    #                         KeyboardButton('COMPUTE')
    #                         ],
    #             resize_keyboard=True,
    #             # one_time_keyboard=True,
    #             selective=True
    #         )
    menu = ReplyKeyboardMarkup(
        resize_keyboard=True, one_time_keyboard=True, selective=True
    )
    # menu.add(KeyboardButton("Add fertilization"))
    # menu.add(KeyboardButton("Add irrigation"))
    menu.add(KeyboardButton("COMPUTE ☘️"))
    await Form.field_main.set()
    # await bot.send_message(
    #     message.from_user.id,
    #     temp_info[lang],
    #     parse_mode=ParseMode.MARKDOWN,
    # )
    logging.info("We before final keyboarb")
    await message.reply(
        "Select",
        reply_markup=menu,
    )


# Handle invalid crop end date (harvesting)


@dp.message_handler(
    lambda message: not check_date_format(message)[0], state=Form.add_field_crop_end
)
async def process_crop_end_invalid(message: types.Message, state: FSMContext):
    await log_message(message, state)
    lang = "EN"
    return await message.reply(
        ru_en_dict["Введите дату сборa урожая в формате день.месяц, 30.09"][lang]
    )


# Handle main field menu callbacks
@dp.message_handler(state=Form.field_main)
# @dp.callback_query_handler(lambda callback_query: True, state=Form.field_main)
async def process_callback_main_field_main(message: types.Message, state: FSMContext):
    await log_message(message, state)
    lang = language.get(message.chat.id, "EN")
    # await bot.edit_message_reply_markup(
    #     message.chat.id,
    #     message.message_id,
    #     reply_markup=None,
    # )

    # Formatted message with field info
    temp_keyboard_inline_main = {
        "RU": kb.inline_main_field_kb,
        "EN": kb.inline_main_field_kb_en,
    }
    temp_irrigation_format = {
        "RU": kb.irrigation_format_text,
        "EN": kb.irrigation_format_text_en,
    }
    temp_npk_format = {"RU": kb.npk_format_text, "EN": kb.npk_format_text_en}
    temp_main_kb = {"RU": kb.inline_main_kb, "EN": kb.inline_main_kb_en}
    temp_kb_back = {"RU": kb.back_markup, "EN": kb.back_markup_en}
    code = message.text
    # Add irrigation
    if code == "Add irrigation":
        await Form.add_irrigation.set()
        await bot.send_message(
            message.from_user.id,
            temp_irrigation_format[lang],
            reply_markup=temp_kb_back[lang],
            parse_mode=ParseMode.MARKDOWN,
        )

    # Add fertilization aka NPK
    elif code == "Add fertilization":
        await Form.add_npk.set()
        await bot.send_message(
            message.from_user.id,
            temp_npk_format[lang],
            reply_markup=temp_kb_back[lang],
            parse_mode=ParseMode.MARKDOWN,
        )

    # Delete irrigation
    elif code == "Remove irrigation":
        await Form.del_irrigation.set()
        async with state.proxy() as data:
            all_irrigations = await db.get_irrigations(data["current_field"])
            irrigations_btns = [
                InlineKeyboardButton(
                    f"{irr.date} {float(irr.amount): .2f}",  # type: ignore
                    callback_data=f"irrigation_{irr.id}",
                )
                for irr in all_irrigations
            ]
            irrigations_btns.append(
                InlineKeyboardButton(
                    ru_en_dict["Назад"][lang], callback_data=f"irrigation_cancel"
                )
            )
            inline_irrigation_kb = InlineKeyboardMarkup().add(*irrigations_btns)
        await bot.send_message(
            message.from_user.id,
            ru_en_dict["Выберите, какое событие удалить:"][lang],
            reply_markup=inline_irrigation_kb,
        )

    # Delete fertilization aka NPK
    elif code == "Remove fertilization":
        await Form.del_npk.set()
        async with state.proxy() as data:
            all_npks = await db.get_npks(data["current_field"])
            npks_btns = [
                InlineKeyboardButton(
                    f"{npk.date} {'/'.join(list(map(str, npk.npk)))}",
                    callback_data=f"npk_{npk.id}",
                )
                for npk in all_npks
            ]
            npks_btns.append(
                InlineKeyboardButton(
                    ru_en_dict["Назад"][lang], callback_data=f"npk_cancel"
                )
            )
            inline_npk_kb = InlineKeyboardMarkup().add(*npks_btns)
        await bot.send_message(
            message.from_user.id,
            ru_en_dict["Выберите, какое событие удалить:"][lang],
            reply_markup=inline_npk_kb,
        )

    # Delete field
    elif code == "Remove field":
        async with state.proxy() as data:
            await db.delete_field(data["current_field"])
            data["current_field"] = None
            data["fields"] = await db.get_user_field_dicts(message.from_user.id)
            await Form.main.set()
        await bot.send_message(
            message.from_user.id,
            ru_en_dict["Поле удалено, выберите действие:"][lang],
            reply_markup=temp_main_kb[lang],
        )

    # Back to field choosing
    elif code == "Back to select field":
        await Form.main.set()
        await bot.send_message(
            message.from_user.id,
            ru_en_dict["Выберите действие:"][lang],
            reply_markup=temp_main_kb[lang],
        )

    # Calculate
    elif "COMPUTE" in code:

        logging.info("here we go")
        await Form.calculating.set()
        async with state.proxy() as data:
            cur_field = data["current_field"]
            os.makedirs(f"/home/results/{message.from_user.id}/", exist_ok=True)
            counter = 0
            # input_agro_calendar = f"./home/results/{callback_query.from_user.id}/{cur_field}_agro_calendar_"+"{}.json"
            input_agro_calendar_prefix = (
                f"/home/results/{message.from_user.id}/{cur_field}_agro_calendar_"
            )
            while os.path.isfile(input_agro_calendar_prefix + f"{counter}.json"):
                counter += 1
            # input_agro_calendar.format(counter)
            input_agro_calendar = input_agro_calendar_prefix + f"{counter}.json"
            plot_name = f"/home/results/{message.from_user.id}/{cur_field}_results_{counter}.png"
            json.dump(
                data["fields"][data["current_field"]],
                open(input_agro_calendar, "w+"),
                ensure_ascii=False,
            )

        await bot.send_message(
            message.from_user.id,
            (
                "The model calculation for the field is started.\n"
                "This operation takes about a minute...\n"
                "More about PCSE/WOFOST: [Docs](https://wofost.readthedocs.io/en/latest/)\n"
                "If nothing happens after 5 minutes, type /cancel and try again with /start"
            ),
            parse_mode=ParseMode.MARKDOWN,
        )

        # command = f"python3 bot_crop_model.py --path_to_data_dir ./input_data --path_to_user_file {input_agro_calendar} \
        #             --path_to_CSV_weather ./input_data/weather --plot_name {plot_name} --field_plot_name {field_plot_name} --user_language {lang}"
        # logging.info(command)

        with open(input_agro_calendar, "r") as f:
            user_parameters = json.load(f)

        logging.info("Weather loading...")
        wdp = AWS_WOFOST(
            latitude=user_parameters["latitude"],
            longitude=user_parameters["longitude"],
            ds_solar=aws.ds_solar,
            ds_weather=aws.ds_weather,
        )
        # TO-DO: Add weather
        logging.info("Weather donwloaded✅")
        WOFOST = Irrigation()

        logging.info("Start crop model")

        content = WOFOST.compute(
            path_to_data_dir="/home/src/input_data",
            path_to_user_file=input_agro_calendar,
            output_plot_name=plot_name,
            weather=wdp,
        )
        if content["status"] == "Error":
            await bot.send_message(
                message.from_user.id,
                "We have server error. Please try again" + content["info"],
            )
        logging.info("Done crop model")
        # loop = asyncio.get_event_loop()
        # # executor = ProcessPoolExecutor(max_workers=2)
        # # executor = ThreadPoolExecutor(max_workers=2)
        # fut = loop.run_in_executor(executor, time.sleep, 10)

        # fut = loop.run_in_executor(
        #     executor,
        #     partial(
        #         WOFOST.compute,
        #         path_to_data_dir="/home/src/input_data",
        #         path_to_user_file=input_agro_calendar,
        #         output_plot_name=plot_name,
        #         weather=wdp,
        #     ),
        # )
        # res = await fut

        body = os.path.splitext(plot_name)[0]
        plots_suffix = ["historical_yield", "LAI", "TWSO", "SM", "sowing_dates"]
        for name in plots_suffix:
            new_name = f"{body}_{name}.png"
            if os.path.exists(new_name):
                await bot.send_photo(message.from_user.id, photo=open(new_name, "rb"))
            else:
                pass
        await Form.main.set()
        menu = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Add field"), KeyboardButton(text="Select field")]
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        await bot.send_message(
            message.from_user.id,
            ru_en_dict["Посчитано. Выберите новое действие:"][lang],
            reply_markup=menu,
        )

    # Field information
    if code[:5] == "field":
        await Form.field_main.set()
        async with state.proxy() as data:
            data["current_field"] = code.split("_")[1]
            await Form.field_main.set()

            temp_kb_inline_main = {
                "RU": kb.inline_main_field_kb,
                "EN": kb.inline_main_field_kb_en,
            }

            temp_info = {
                "RU": kb.print_field_info(data["fields"][data["current_field"]]),
                "EN": kb.print_field_info_en(data["fields"][data["current_field"]]),
            }

            await bot.send_message(
                message.from_user.id,
                temp_info[lang],
                reply_markup=temp_kb_inline_main[lang],
                parse_mode=ParseMode.MARKDOWN,
            )


def check_irrigation_format(message):
    date_format = "%d.%m.%Y"
    irr_list = []
    for chunk in message.text.replace(", ", ",").split(","):
        if len(chunk.split(" ")) != 2:
            return False, None
        else:
            date_str, amount_str = chunk.split(" ")
            try:
                irr_date = datetime.datetime.strptime(date_str + ".2023", date_format)
                irr_amount = float(amount_str)
                irr_list.append([irr_date, irr_amount])
            except:
                return False, None
    return True, irr_list


# Handle irrigation
@dp.message_handler(
    lambda message: message.text == ru_en_dict["Готово"][language[message.chat.id]]
    or check_irrigation_format(message)[0],
    state=Form.add_irrigation,
)
async def process_irrigation(message: types.Message, state: FSMContext):

    lang = "EN"
    async with state.proxy() as data:
        if message.text == ru_en_dict["Готово"][lang]:
            await Form.field_main.set()
            agro_dict = data["fields"][data["current_field"]]
            temp_kb_agro_dict = {
                "RU": kb.print_field_info(agro_dict),
                "EN": kb.print_field_info_en(agro_dict),
            }
            temp_kb_inline_main = {
                "RU": kb.inline_main_field_kb,
                "EN": kb.inline_main_field_kb_en,
            }
            await bot.send_message(
                message.chat.id,
                temp_kb_agro_dict[lang],
                reply_markup=temp_kb_inline_main[lang],
                parse_mode=ParseMode.MARKDOWN,
            )

        else:
            for irr_item in check_irrigation_format(message)[1]:  # type: ignore
                irr_date, irr_amount = irr_item
                irrigation_id = str(uuid.uuid4())

                await db.add_irrigation(
                    irrigation_id, data["current_field"], irr_date, irr_amount
                )
            data["fields"] = await db.get_user_field_dicts(message.chat.id)
            temp_kb_back = {"RU": kb.back_markup, "EN": kb.back_markup_en}
            temp_irr_added_text = {
                "RU": kb.irrigations_added_text(check_irrigation_format(message)[1]),
                "EN": kb.irrigations_added_text_en(check_irrigation_format(message)[1]),
            }
            await bot.send_message(
                message.chat.id,
                temp_irr_added_text[lang],
                reply_markup=temp_kb_back[lang],
                parse_mode=ParseMode.MARKDOWN,
            )


# Handle irrigation invalid
@dp.message_handler(
    lambda message: message.text != ru_en_dict["Готово"][language[message.chat.id]]
    and not check_irrigation_format(message)[0],
    state=Form.add_irrigation,
)
async def process_irrigation_invalid(message: types.Message, state: FSMContext):
    lang = "EN"
    temp_kb_back = {"RU": kb.back_markup, "EN": kb.back_markup_en}
    temp_irrigation_format = {
        "RU": kb.irrigation_format_text,
        "EN": kb.irrigation_format_text_en,
    }
    return await message.reply(
        temp_irrigation_format[lang],
        reply_markup=temp_kb_back[lang],
        parse_mode=ParseMode.MARKDOWN,
    )


def check_npk_format(message):
    date_format = "%d.%m.%Y"
    npk_list = []
    for chunk in message.text.replace(", ", ",").split(","):
        if len(chunk.split(" ")) != 2:
            return False, None
        else:
            date_str, amount_str = chunk.split(" ")
            try:
                npk_date = datetime.datetime.strptime(date_str + ".2023", date_format)
                npk_amount = [
                    float(x) for x in amount_str.replace("/ ", "/").split("/")
                ]
                npk_list.append([npk_date, npk_amount])
            except:
                return False, None

    return True, npk_list


# Handle NPK invalid
@dp.message_handler(
    lambda message: message.text != ru_en_dict["Готово"][language[message.chat.id]]
    and not check_npk_format(message)[0],
    state=Form.add_npk,
)
async def process_npk_invalid(message: types.Message, state: FSMContext):

    lang = "EN"
    temp_npk_format = {"RU": kb.npk_format_text, "EN": kb.npk_format_text_en}
    temp_kb_back = {"RU": kb.back_markup, "EN": kb.back_markup_en}
    return await message.reply(
        temp_npk_format[lang],
        reply_markup=temp_kb_back[lang],
        parse_mode=ParseMode.MARKDOWN,
    )


# Handle NPK
@dp.message_handler(
    lambda message: message.text == ru_en_dict["Готово"][language[message.chat.id]]
    or check_npk_format(message)[0],
    state=Form.add_npk,
)
async def process_npk(message: types.Message, state: FSMContext):

    lang = "EN"
    async with state.proxy() as data:
        if message.text == ru_en_dict["Готово"][lang]:
            await Form.field_main.set()
            agro_dict = data["fields"][data["current_field"]]

            temp_kb_inline_main = {
                "RU": kb.inline_main_field_kb,
                "EN": kb.inline_main_field_kb_en,
            }
            temp_info_agro_dict = {
                "RU": kb.print_field_info(agro_dict),
                "EN": kb.print_field_info_en(agro_dict),
            }
            await bot.send_message(
                message.chat.id,
                temp_info_agro_dict[lang],
                reply_markup=temp_kb_inline_main[lang],
                parse_mode=ParseMode.MARKDOWN,
            )

        else:
            for npk_item in check_npk_format(message)[1]:  # type: ignore
                npk_date, npk_amount = npk_item
                npk_id = str(uuid.uuid4())
                await db.add_npk(npk_id, data["current_field"], npk_date, npk_amount)
            data["fields"] = await db.get_user_field_dicts(message.chat.id)
            temp_keyboard = {"RU": kb.back_markup, "EN": kb.back_markup_en}
            temp_kb_npk_added = {
                "RU": kb.npks_added_text(check_npk_format(message)[1]),
                "EN": kb.npks_added_text_en(check_npk_format(message)[1]),
            }
            await bot.send_message(
                message.chat.id,
                temp_kb_npk_added[lang],
                reply_markup=temp_keyboard[lang],
                parse_mode=ParseMode.MARKDOWN,
            )


# Handle delete irrigation
@dp.callback_query_handler(lambda callback_query: True, state=Form.del_irrigation)
async def process_callback_irrigation(
    callback_query: types.CallbackQuery, state: FSMContext
):

    lang = language.get(callback_query.message.chat.id, "EN")
    await bot.edit_message_reply_markup(
        callback_query.message.chat.id,
        callback_query.message.message_id,
        reply_markup=None,
    )
    code = callback_query.data
    user_id = callback_query.from_user.id
    async with state.proxy() as data:
        if code[:10] == "irrigation":
            if code != "irrigation_cancel":
                irrigation_id = code.split("_")[1]
                await db.delete_irrigation(int(irrigation_id))
                data["fields"] = await db.get_user_field_dicts(
                    callback_query.from_user.id
                )
                await bot.send_message(
                    callback_query.from_user.id,
                    ru_en_dict["Полив удален"][lang],
                    reply_markup=ReplyKeyboardRemove(),
                )
            await Form.field_main.set()

            temp_info = {
                "RU": kb.print_field_info(data["fields"][data["current_field"]]),
                "EN": kb.print_field_info_en(data["fields"][data["current_field"]]),
            }

            temp_keyboard = {
                "RU": kb.inline_main_field_kb,
                "EN": kb.inline_main_field_kb_en,
            }

            inline_main_field_btns_en = [
                KeyboardButton("Add irrigation", text="mf_add_irrigation"),
                KeyboardButton("Add fertilization", text="mf_add_npk"),
                KeyboardButton("Remove irrigation", text="mf_del_irrigation"),
                KeyboardButton("Remove fertilization", text="mf_del_npk"),
                KeyboardButton("Remove field", text="mf_del_field"),
                KeyboardButton("Back to select field", text="mf_back"),
                KeyboardButton("COMPUTE", text="mf_calc"),
            ]
            inline_main_field_kb_en = ReplyKeyboardMarkup(row_width=2).add(
                *inline_main_field_btns_en
            )
            await bot.send_message(
                callback_query.from_user.id,
                temp_info[lang],
                reply_markup=inline_main_field_kb_en,
                parse_mode=ParseMode.MARKDOWN,
            )


# Handle delete NPK
@dp.callback_query_handler(lambda callback_query: True, state=Form.del_npk)
async def process_callback_npk(callback_query: types.CallbackQuery, state: FSMContext):

    lang = language.get(callback_query.message.chat.id, "EN")
    await bot.edit_message_reply_markup(
        callback_query.message.chat.id,
        callback_query.message.message_id,
        reply_markup=None,
    )
    code = callback_query.data
    async with state.proxy() as data:
        if code[:3] == "npk":
            if code != "npk_cancel":
                npk_id = code.split("_")[1]
                await db.delete_npk(npk_id)
                data["fields"] = await db.get_user_field_dicts(
                    callback_query.from_user.id
                )
                await bot.send_message(
                    callback_query.from_user.id,
                    ru_en_dict["Внесение удобрений удалено"][lang],
                    reply_markup=ReplyKeyboardRemove(),
                )
            await Form.field_main.set()
            temp_info = {
                "RU": kb.print_field_info(data["fields"][data["current_field"]]),
                "EN": kb.print_field_info_en(data["fields"][data["current_field"]]),
            }
            temp_keyboard = {
                "RU": kb.inline_main_field_kb,
                "EN": kb.inline_main_field_kb_en,
            }
            await bot.reply(
                callback_query.from_user.id,
                temp_info[lang],
                reply_markup=temp_keyboard[lang],
                parse_mode=ParseMode.MARKDOWN,
            )


# async def main() -> None:
#     # And the run events dispatching
#     await dp.start_polling(bot)


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
    # asyncio.run(main())
