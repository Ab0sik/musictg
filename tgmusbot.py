import telebot
from telebot import types
import requests
from pytubefix import Search, YouTube
from io import BytesIO
import os
from flask import Flask, request

# Конфигурация бота
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN", "7993987166:AAFKhbLsUWf-1SzEuOCU8acYt_OxCZR-9Qs")
BOT_NAME = "Wilderry"
BOT_USERNAME = "wilderrybot"
BOT_DESCRIPTION = """
<b>🔍 Музыкальный бот с быстрым поиском</b>

🎵 Найду любую музыку или клип на YouTube
📥 Скачаю в MP3 (аудио) или MP4 (видео)
⚡ Работает быстро и без ограничений

Просто введи название песни или исполнителя!
"""

# Инициализация бота и Flask приложения
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)

# Инициализация хранилища данных
user_data = {}

def create_main_menu():
    """Создает главное меню с кнопками"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        types.KeyboardButton('🔍 Поиск музыки'),
        types.KeyboardButton('📥 Мои загрузки'),
        types.KeyboardButton('❓ Помощь'),
        types.KeyboardButton('⭐ О боте')
    ]
    markup.add(*buttons)
    return markup


def create_back_button():
    """Создает кнопку 'Назад'"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('⬅️ Назад'))
    return markup


def create_search_results_markup(results):
    """Создает инлайн-кнопки с результатами поиска"""
    markup = types.InlineKeyboardMarkup()
    for i, video in enumerate(results[:5], 1):
        btn_text = f"{i}. {video.title[:25]} - {video.author[:15]}"
        markup.add(types.InlineKeyboardButton(
            btn_text,
            callback_data=f"select_{video.video_id}"
        ))
    return markup


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Обработчик команд /start и /help"""
    welcome_text = f"""
    <b>{BOT_NAME}</b> (@{BOT_USERNAME})

    {BOT_DESCRIPTION}
    """
    bot.send_message(
        message.chat.id,
        welcome_text,
        reply_markup=create_main_menu()
    )


@bot.message_handler(func=lambda m: m.text == '⬅️ Назад')
def back_to_menu(message):
    """Возврат в главное меню"""
    bot.send_message(
        message.chat.id,
        "Главное меню:",
        reply_markup=create_main_menu()
    )


@bot.message_handler(func=lambda m: m.text == '🔍 Поиск музыки')
def start_search(message):
    """Начало поиска музыки"""
    msg = bot.send_message(
        message.chat.id,
        "🔍 <b>Введите название песни или исполнителя:</b>",
        reply_markup=create_back_button()
    )
    bot.register_next_step_handler(msg, process_search_query)


@bot.message_handler(func=lambda m: m.text == '❓ Помощь')
def show_help(message):
    """Показывает справку"""
    help_text = """
    <b>❓ Как использовать бота:</b>

    1. Нажмите <b>'🔍 Поиск музыки'</b>
    2. Введите название песни
    3. Выберите трек из списка
    4. Укажите формат (MP3/MP4)
    5. Получите файл!

    <i>Для возврата используйте кнопку '⬅️ Назад'</i>
    """
    bot.send_message(
        message.chat.id,
        help_text,
        reply_markup=create_back_button()
    )


@bot.message_handler(func=lambda m: m.text == '⭐ О боте')
def about_bot(message):
    """Информация о боте"""
    about_text = f"""
    <b>{BOT_NAME}</b> (@{BOT_USERNAME})

    Версия: 2.0
    Обновлено: 15.07.2023

    <b>Возможности:</b>
    - Поиск музыки на YouTube
    - Скачивание в MP3/MP4
    - Быстрая загрузка
    - Удобный интерфейс

    Разработчик: @YourUsername
    """
    bot.send_message(
        message.chat.id,
        about_text,
        reply_markup=create_back_button()
    )


def process_search_query(message):
    """Обрабатывает поисковый запрос"""
    if message.text == '⬅️ Назад':
        return back_to_menu(message)

    try:
        query = message.text
        bot.send_message(
            message.chat.id,
            f"🔍 Ищу: <i>{query}</i>...",
            reply_markup=create_back_button()
        )

        # Поиск на YouTube
        search_results = Search(query).results[:5]

        if not search_results:
            bot.send_message(
                message.chat.id,
                "❌ Ничего не найдено. Попробуйте другой запрос.",
                reply_markup=create_back_button()
            )
            return

        # Сохраняем результаты
        user_data[message.chat.id] = {
            'last_search': query,
            'results': {vid.video_id: vid for vid in search_results}
        }

        # Показываем результаты
        bot.send_message(
            message.chat.id,
            "🎵 <b>Найденные треки:</b>",
            reply_markup=create_search_results_markup(search_results)
        )

    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"⚠️ Ошибка: {str(e)}",
            reply_markup=create_back_button()
        )


@bot.callback_query_handler(func=lambda c: c.data.startswith('select_'))
def show_selected_track(call):
    """Показывает выбранный трек"""
    try:
        chat_id = call.message.chat.id
        video_id = call.data.split('_')[1]

        if chat_id not in user_data or video_id not in user_data[chat_id]['results']:
            bot.answer_callback_query(call.id, "❌ Ошибка. Начните поиск заново.")
            return

        video = user_data[chat_id]['results'][video_id]

        # Отправляем обложку
        bot.send_photo(
            chat_id,
            video.thumbnail_url,
            caption=f"🎵 <b>{video.title}</b>\n👤 {video.author}\n\n<b>Выберите формат:</b>"
        )

        # Кнопки выбора формата
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("🎶 Скачать MP3", callback_data=f"dl_{video_id}_mp3"),
            types.InlineKeyboardButton("🎥 Скачать MP4", callback_data=f"dl_{video_id}_mp4")
        )
        markup.add(types.InlineKeyboardButton("🔍 Новый поиск", callback_data="new_search"))

        bot.send_message(chat_id, "⬇️ <b>Выберите действие:</b>", reply_markup=markup)
        bot.delete_message(chat_id, call.message.message_id)

    except Exception as e:
        bot.send_message(
            call.message.chat.id,
            f"⚠️ Ошибка: {str(e)}",
            reply_markup=create_back_button()
        )


@bot.callback_query_handler(func=lambda c: c.data == "new_search")
def new_search(call):
    """Начинает новый поиск"""
    bot.send_message(
        call.message.chat.id,
        "🔍 <b>Введите название песни или исполнителя:</b>",
        reply_markup=create_back_button()
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith('dl_'))
def download_track(call):
    """Скачивает и отправляет трек"""
    try:
        chat_id = call.message.chat.id
        _, video_id, format_type = call.data.split('_')

        if chat_id not in user_data or video_id not in user_data[chat_id]['results']:
            bot.answer_callback_query(call.id, "❌ Ошибка. Начните заново.")
            return

        video = user_data[chat_id]['results'][video_id]
        bot.answer_callback_query(call.id, "⏳ Загружаю... Пожалуйста, подождите.")

        # Скачивание в оперативную память
        buffer = BytesIO()

        if format_type == "mp3":
            # Аудио поток
            audio_stream = video.streams.filter(only_audio=True).first()
            audio_stream.stream_to_buffer(buffer)
            buffer.seek(0)

            # Отправка MP3
            bot.send_audio(
                chat_id,
                buffer,
                title=video.title,
                performer=video.author,
                thumb=requests.get(video.thumbnail_url).content
            )

        elif format_type == "mp4":
            # Видео поток (360p)
            video_stream = video.streams.filter(
                file_extension="mp4",
                progressive=True
            ).order_by('resolution').desc().first()

            video_stream.stream_to_buffer(buffer)
            buffer.seek(0)

            # Отправка MP4
            bot.send_video(
                chat_id,
                buffer,
                caption=f"🎥 <b>{video.title}</b>\n👤 {video.author}"
            )

        # Удаляем сообщение с кнопками
        bot.delete_message(chat_id, call.message.message_id)

    except Exception as e:
        bot.send_message(
            call.message.chat.id,
            f"⚠️ Ошибка при загрузке: {str(e)}",
            reply_markup=create_back_button()
        )

# Вебхук обработчики
@app.route('/', methods=['GET'])
def home():
    return {"status": "Bot is running", "deploy": os.getenv("RENDER_EXTERNAL_URL")}, 200

@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    webhook_url = f"https://telegram-bot-o8wp.onrender.com/{BOT_TOKEN}"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    return f"Webhook set to {webhook_url}", 200

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.method == "POST":
        update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
        bot.process_new_updates([update])
    return "ok", 200

@app.route('/ping')
def ping():
    return "pong", 200

if __name__ == '__main__':
    # Для локального тестирования с polling
    if os.getenv("ENVIRONMENT") == "development":
        print(f"Бот {BOT_NAME} (@{BOT_USERNAME}) запущен в режиме polling!")
        bot.infinity_polling()
    else:
        # Для production с вебхуками
        app.run(host='0.0.0.0', port=5000)
