import os
import aiohttp
import mysql.connector
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.types import MenuButtonCommands, CallbackQuery, BotCommand, BotCommandScopeDefault
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import asyncio
from flask import Flask
from threading import Thread

# Загружаем переменные окружения из .env
load_dotenv()

# Получаем токен
TOKEN = os.getenv("TOKEN")
SELF_PING_URL = os.getenv("SELF_PING_URL")

# Инициализируем бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()


# Подключение к базе данных MySQL
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT"))
    )

''' 
# Хэндлер для команды /start
@dp.message(Command('start'))
async def start(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Девушки юморклуба", callback_data="show_girls")]
    ])
    await message.answer()#("Привет! Выберите опцию:", reply_markup=keyboard)
'''
app = Flask(__name__)

@app.route('/')
def index():
    return "Бот работает в фоновом режиме!"

async def on_startup():
    await set_bot_commands(bot)
    await set_menu_button(bot)

async def set_menu_button(bot: Bot):
    await bot.set_chat_menu_button(menu_button=MenuButtonCommands())

async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Запуск бота"),
        BotCommand(command="girls", description="Девушки юморклуба")
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())

# Функция self-ping, чтобы Render не засыпал
async def keep_awake():
    while True:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(SELF_PING_URL) as response:
                    print(f"Self-ping: {response.status}")
            except Exception as e:
                print(f"Self-ping error: {e}")
        await asyncio.sleep(300)  # Пинг каждые 5 минут

# Хэндлер для кнопки "Девушки юморклуба"
#@dp.callback_query(lambda c: c.data == "show_girls")
@dp.message(Command('girls'))
@dp.message(Command('start'))
async def show_girls(message: types.Message):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT GirlID, Name FROM girls")
    girls = cursor.fetchall()

    girls.sort(key=lambda x: x['Name'])

    keyboard = InlineKeyboardBuilder()
    for girl in girls:
        keyboard.button(text=girl['Name'], callback_data=f"show_info_{girl['GirlID']}")

    keyboard.adjust(2)
    keyboard = keyboard.as_markup()

    await bot.send_message(message.chat.id, "Наши прекрасные девушки:", reply_markup=keyboard)


@dp.callback_query(lambda c: c.data.startswith("show_info_"))
async def show_girl_info(callback_query: CallbackQuery):
    girl_id = callback_query.data.split("_")[2]

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM girls WHERE GirlID = %s", (girl_id,))
    girl = cursor.fetchone()

    if girl:
        cursor.execute("""
            SELECT f.Name 
            FROM flowers f 
            JOIN girlflowers gf ON gf.FlowerID = f.FlowerID 
            WHERE gf.GirlID = %s
        """, (girl_id,))
        flowers = cursor.fetchall()

        cursor.execute("""
            SELECT s.Name 
            FROM sweets s 
            JOIN girlsweets gs ON gs.SweetID = s.SweetID 
            WHERE gs.GirlID = %s
        """, (girl_id,))
        sweets = cursor.fetchall()

        cursor.execute("""
            SELECT fr.Name 
            FROM fruits fr 
            JOIN girlfruits gf ON gf.FruitID = fr.FruitID 
            WHERE gf.GirlID = %s
        """, (girl_id,))
        fruits = cursor.fetchall()

        info = f"<b>💖 {girl['Name']} 💖</b>\n\n"

        info += f"<b>🌸 Любимые цветы:</b> " + (", ".join(
            [flower['Name'] for flower in flowers]) if flowers else "Нет любимых цветов.") + "\n"

        info += f"<b>🍬 Любимые сладости:</b> " + (", ".join(
            [sweet['Name'] for sweet in sweets]) if sweets else "Нет любимых сладостей.") + "\n"

        info += f"<b>🍎 Любимые фрукты/ягоды:</b> " + (", ".join(
            [fruit['Name'] for fruit in fruits]) if fruits else "Нет любимых фруктов.") + "\n\n"

        info += f"<i>📝 Дополнительная информация:</i> {girl['Info']}" if girl['Info'] != None else ""

        await bot.send_message(callback_query.from_user.id, info, parse_mode="HTML")
    else:
        await bot.send_message(callback_query.from_user.id, "Девушка не найдена.")


# Функция для запуска бота
async def start_polling():
    try:
        print("Запуск бота...")
        asyncio.create_task(keep_awake())
        await on_startup()
        await dp.start_polling(bot)
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")
    finally:
        await bot.close()


# Функция для запуска Flask-приложения
def run_flask():
    app.run(host="0.0.0.0", port=5000)


# Основная функция, которая запускает Flask и бот
def run():
    # Запускаем Flask-приложение в отдельном потоке
    thread = Thread(target=run_flask)
    thread.daemon = True
    thread.start()

    # Запуск бота
    asyncio.run(start_polling())


if __name__ == "__main__":
    run()
