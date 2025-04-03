import os
import mysql.connector
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import asyncio

# Загружаем переменные окружения из .env
load_dotenv()

# Получаем токен
TOKEN = os.getenv("TOKEN")

# Инициализируем бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()


# Подключение к базе данных MySQL
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),  # Хост базы данных из переменных окружения
        user=os.getenv("DB_USER"),  # Имя пользователя базы данных
        password=os.getenv("DB_PASSWORD"),  # Пароль
        database=os.getenv("DB_NAME"),  # Имя базы данных
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

# Хэндлер для кнопки "Девушки юморклуба"
@dp.callback_query(lambda c: c.data == "show_girls")
@dp.message(Command('start'))
async def show_girls(callback_query: CallbackQuery):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT GirlID, Name FROM girls")
    girls = cursor.fetchall()

    girls.sort(key=lambda x: x['Name'])

    # Создаём инлайн-кнопки с именами девушек
    keyboard = InlineKeyboardBuilder()
    for girl in girls:
        keyboard.button(text=girl['Name'], callback_data=f"show_info_{girl['GirlID']}")

    keyboard.adjust(2)
    keyboard = keyboard.as_markup()

    await bot.send_message(callback_query.from_user.id, "Наши прекрасные девушки:", reply_markup=keyboard)


# Хэндлер для выбора конкретной девушки
@dp.callback_query(lambda c: c.data.startswith("show_info_"))
async def show_girl_info(callback_query: CallbackQuery):
    girl_id = callback_query.data.split("_")[2]

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Получаем информацию о девушке
    cursor.execute("SELECT * FROM girls WHERE GirlID = %s", (girl_id,))
    girl = cursor.fetchone()

    if girl:
        # Получаем любимые цветы, сладости и фрукты
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

        # Формируем информацию
        info = f"<b>💖 {girl['Name']} 💖</b>\n\n"

        # Добавляем любимые цветы
        info += f"<b>🌸 Любимые цветы:</b> " + (", ".join(
            [flower['Name'] for flower in flowers]) if flowers else "Нет любимых цветов.") + "\n"

        # Добавляем любимые сладости
        info += f"<b>🍬 Любимые сладости:</b> " + (", ".join(
            [sweet['Name'] for sweet in sweets]) if sweets else "Нет любимых сладостей.") + "\n"

        # Добавляем любимые фрукты
        info += f"<b>🍎 Любимые фрукты/ягоды:</b> " + (", ".join(
            [fruit['Name'] for fruit in fruits]) if fruits else "Нет любимых фруктов.") + "\n\n"

        info += f"<i>📝 Дополнительная информация:</i> {girl['Info']}" if girl['Info']!=None else ""

        # Отправляем информацию пользователю
        await bot.send_message(callback_query.from_user.id, info, parse_mode="HTML")
    else:
        await bot.send_message(callback_query.from_user.id, "Девушка не найдена.")


# Запуск бота
async def main():
    try:
        print("Бот запускается...")
        await dp.start_polling(bot)
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
