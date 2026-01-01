import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiocryptopay import AioCryptoPay, Networks
from dotenv import load_dotenv
import os

load_dotenv()

db_url = os.getenv("BOT_TOKIN")
api_key = os.getenv("CRYPTO_BOT_TOKIN")
channel_code = os.getenv("CHANNEL_COKE")

print(db_url)
print(api_key)
print(channel_code)

# ================= НАСТРОЙКИ =================
BOT_TOKEN = "db_url"
CRYPTO_BOT_TOKEN = "api_key"
CHANNEL_ID = channel_code  # ID вашего канала (начинается с -100)
PRICE_AMOUNT = 10  # Цена подписки
PRICE_CURRENCY = "USDT"  # Валюта (USDT, TON, BTC)

# Выбираем сеть: MAIN_NET (реальные деньги) или TEST_NET (для тестов)
# Когда будете готовы к реальным деньгам, поменяйте на Networks.MAIN_NET
NETWORK = Networks.MAIN_NET
# =============================================

# Инициализация
bot = Bot(token=db_url)
dp = Dispatcher()
crypto = AioCryptoPay(token=api_key, network=NETWORK)

logging.basicConfig(level=logging.INFO)

# Хранилище счетов (в реальном проекте лучше использовать базу данных SQLite)
# Формат: {user_id: invoice_id}
user_invoices = {}

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = [
        [types.InlineKeyboardButton(text="💎 Купить доступ (10 USDT)", callback_data="buy_sub")]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)
    
    await message.answer(
        f"Привет, {message.from_user.first_name}!\n"
        "Это бот для доступа в приватный канал с AI-контентом.\n"
        "Оплата принимается в криптовалюте анонимно.",
        reply_markup=keyboard
    )

@dp.callback_query(F.data == "buy_sub")
async def process_buy(callback: types.CallbackQuery):
    # Создаем счет в CryptoBot
    try:
        invoice = await crypto.create_invoice(asset=PRICE_CURRENCY, amount=PRICE_AMOUNT)
        
        # Сохраняем ID счета для этого пользователя
        user_invoices[callback.from_user.id] = invoice.invoice_id
        
        # Клавиатура с ссылкой на оплату и проверкой
        kb = [
            [types.InlineKeyboardButton(text="🔗 Оплатить", url=invoice.bot_invoice_url)],
            [types.InlineKeyboardButton(text="✅ Я оплатил", callback_data="check_pay")]
        ]
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)
        
        await callback.message.edit_text(
            f"Счет создан!\nСумма: {PRICE_AMOUNT} {PRICE_CURRENCY}\n\n"
            "1. Нажмите «Оплатить» и переведите средства.\n"
            "2. После оплаты нажмите «Я оплатил».",
            reply_markup=keyboard
        )
    except Exception as e:
        await callback.message.answer(f"Ошибка при создании счета: {e}")
        
@dp.callback_query(F.data == "check_pay")
async def process_check(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    invoice_id = user_invoices.get(user_id)
    
    if not invoice_id:
        await callback.answer("Счет не найден. Попробуйте создать новый.", show_alert=True)
        return

    # Проверяем статус счета через API
    invoices = await crypto.get_invoices(invoice_ids=str(invoice_id))
    
    if invoices and invoices[0].status == 'paid':
        # ОПЛАТА ПРОШЛА!
        
        # Генерируем одноразовую ссылку (работает для 1 человека)
        try:
            invite_link = await bot.create_chat_invite_link(
                chat_id=CHANNEL_ID,
                member_limit=1,  # Ссылка только для одного
                name=f"User {user_id}" # Название ссылки для статистики админа
            )
            
            await callback.message.edit_text(
                "✅ Оплата подтверждена!\n\n"
                f"Вот твоя ссылка на канал: {invite_link.invite_link}\n"
                "Она действует только один раз."
            )
            # Очищаем сохраненный счет
            del user_invoices[user_id]
            
        except Exception as e:
            await callback.message.answer(f"Оплата прошла, но не удалось создать ссылку. Напишите админу. Ошибка: {e}")
            
    else:
        # Оплата еще не дошла или счет не оплачен
        await callback.answer("Оплата пока не найдена. Подождите пару минут и нажмите кнопку снова.", show_alert=True)

async def main():
    print("Бот запущен...")
    # Удаляем вебхуки и запускаем поллинг
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
