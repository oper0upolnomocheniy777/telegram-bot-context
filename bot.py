import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message
import requests
import json

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


BOT_TOKEN = "8510069371:AAHIAGl37P4kaYt1gsx9ee-TmiJehn9Wxv4"

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Хранилище контекста для каждого пользователя
user_contexts = {}

def get_user_context(user_id):
    """Получает или создает контекст для пользователя"""
    if user_id not in user_contexts:
        user_contexts[user_id] = []
    return user_contexts[user_id]

def clear_user_context(user_id):
    """Очищает контекст пользователя"""
    user_contexts[user_id] = []

@dp.message(Command("start"))
async def start_command(message: Message):
    """Обработчик команды /start"""
    welcome_text = """
🤖 Бот для лабораторной работы

Я демонстрирую работу системы контекста диалога!

Команды:
/start - начать работу
/clear - очистить историю
/demo - посмотреть текущий контекст

Просто напишите мне сообщение!
    """
    await message.answer(welcome_text)

@dp.message(Command("clear"))
async def clear_command(message: Message):
    """Обработчик команды /clear"""
    user_id = message.from_user.id
    clear_user_context(user_id)
    await message.answer("✅ История диалога очищена!")

@dp.message(Command("demo"))
async def demo_command(message: Message):
    """Показывает текущий контекст"""
    user_id = message.from_user.id
    context_history = get_user_context(user_id)
    
    if len(context_history) == 0:
        await message.answer("📝 История диалога пуста.")
    else:
        history_text = "📋 Текущий контекст диалога:\n\n"
        for i, msg in enumerate(context_history[-6:], 1):  # Последние 6 сообщений
            role = "👤 Вы" if msg["role"] == "user" else "🤖 Бот"
            history_text += f"{i}. {role}: {msg['content']}\n\n"
        
        await message.answer(history_text)

@dp.message(F.text)
async def handle_message(message: Message):
    """Обработчик всех текстовых сообщений"""
    user_id = message.from_user.id
    user_message = message.text
    
    logger.info(f"Сообщение от пользователя {user_id}: {user_message}")
    
    # Получаем контекст пользователя
    conversation_history = get_user_context(user_id)
    
    # Добавляем сообщение пользователя в историю
    conversation_history.append({"role": "user", "content": user_message})
    
    # Показываем статус "печатает"
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    await asyncio.sleep(1)  # Имитируем задержку для реалистичности
    
    try:
        # Пробуем подключиться к LM Studio
        bot_response = await try_lm_studio(conversation_history)
        
        # Если LM Studio не доступен, используем демо-режим
        if bot_response is None:
            bot_response = demo_ai_response(user_message, conversation_history)
        
        # Добавляем ответ бота в историю
        conversation_history.append({"role": "assistant", "content": bot_response})
        
        # Ограничиваем длину истории (последние 10 сообщений)
        if len(conversation_history) > 10:
            user_contexts[user_id] = conversation_history[-8:]
        
        await message.answer(bot_response)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}")
        await message.answer("❌ Произошла ошибка при обработке вашего сообщения.")

async def try_lm_studio(conversation_history):
    """Пробует подключиться к LM Studio (асинхронная версия)"""
    try:
        url = "http://localhost:1234/v1/chat/completions"
        
        payload = {
            "messages": conversation_history,
            "temperature": 0.7,
            "max_tokens": 300,
            "stream": False
        }
        
        # Используем асинхронные запросы через aiohttp
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=30) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    return None
                    
    except Exception as e:
        logger.info(f"LM Studio недоступен: {e}")
        return None

def demo_ai_response(user_message, conversation_history):
    """Демо-режим когда LM Studio не доступен"""
    user_message_lower = user_message.lower()
    
    # Анализируем контекст для более умных ответов
    previous_messages = [msg["content"] for msg in conversation_history if msg["role"] == "user"]
    
    # Простые правила для демонстрации контекста
    if "привет" in user_message_lower:
        return "Привет! Я бот для лабораторной работы. Я помню наш разговор и буду учитывать контекст!"
    
    elif "как тебя зовут" in user_message_lower:
        return "Я демо-бот для лабораторной работы по созданию Telegram ботов с системой контекста диалога!"
    
    elif "что ты помнишь" in user_message_lower or "контекст" in user_message_lower:
        # Демонстрируем работу контекста
        if len(previous_messages) > 1:
            return f"Я помню наши предыдущие сообщения! Мы говорили о: {', '.join(previous_messages[-3:])}\n\nЭто демонстрирует работу системы контекста - бот запоминает историю диалога!"
        else:
            return "Это наше первое сообщение! Напишите еще что-нибудь, и я покажу как работает система контекста."
    
    elif "пока" in user_message_lower or "до свидания" in user_message_lower:
        return "До свидания! Используйте /clear чтобы очистить нашу историю разговора."
    
    elif "лабораторная" in user_message_lower or "задание" in user_message_lower:
        return "Это демонстрация лабораторной работы по созданию Telegram бота с поддержкой контекста диалога!"
    
    else:
        # Умные ответы с учетом контекста
        if len(previous_messages) > 1:
            # Бот "помнит" предыдущие сообщения
            context_aware_responses = [
                f"Интересно! Вы упомянули это после того как говорили о '{previous_messages[-2]}'. Система контекста работает корректно!",
                f"Запрос получен! Я помню что ранее вы писали: '{previous_messages[-2]}'. Контекст сохраняется успешно.",
                f"Сообщение добавлено в историю диалога. Наш разговор включает: {', '.join(previous_messages[-2:])}",
                f"Отлично! Я учитываю контекст нашего разговора, включая ваше предыдущее сообщение о '{previous_messages[-2]}'."
            ]
        else:
            # Первое сообщение
            context_aware_responses = [
                "Первое сообщение получено! Система контекста готова к работе. Напишите еще что-нибудь чтобы увидеть как я запоминаю диалог.",
                "Сообщение сохранено в истории. Это начало нашего диалога - система контекста активирована!",
                "Запрос получен! Теперь я буду помнить этот разговор благодаря системе контекста.",
                "Отлично! Ваше сообщение добавлено в контекст диалога. Продолжайте общение чтобы увидеть как работает система памяти."
            ]
        
        import random
        return random.choice(context_aware_responses)

async def main():
    """Запуск бота"""
    print("=" * 60)
    print("🤖 Бот запущен на Python 3.13!")
    print("💡 Система контекста диалога активна")
    print("🔧 Используется aiogram 3.13.0")
    print("🌐 Бот автоматически определяет доступность LM Studio")
    print("⏹️  Для остановки нажмите Ctrl+C")
    print("=" * 60)
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())