import telebot
from telebot import types
import requests
from pytubefix import Search, YouTube
from io import BytesIO
import os
from flask import Flask, request
import time
from random import randint

# Инициализация Flask
app = Flask(__name__)

# Конфигурация бота
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN", "7993987166:AAFKhbLsUWf-1SzEuOCU8acYt_OxCZR-9Qs")
BOT_NAME = "Wilderry"
BOT_USERNAME = "wilderrybot"
BOT_DESCRIPTION = """
<b>🔍 Музыкальный бот с быстрым поиском</b>
🎵 Найду любую музыку или клип на YouTube
📥 Скачаю в MP3 (аудио) или MP4 (видео)
⚡ Работает быстро и без ограничений
"""

# Инициализация бота
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
user_data = {}

# --- Вспомогательные функции ---
def safe_search(query, max_retries=3):
    """Поиск с повторными попытками"""
    for attempt in range(max_retries):
        try:
            return Search(query, use_oauth=True).results[:5]
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(randint(2, 5))  # Случайная задержка
            else:
                raise e

def create_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        types.KeyboardButton('🔍 Поиск музыки'),
        types.KeyboardButton('❓ Помощь'),
        types.KeyboardButton('⭐ О боте')
    ]
    markup.add(*buttons)
    return markup

# --- Обработчики команд ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.send_message(
        message.chat.id, 
        f"<b>{BOT_NAME}</b>\n{BOT_DESCRIPTION}",
        reply_markup=create_main_menu()
    )

@bot.message_handler(func=lambda m: m.text == '🔍 Поиск музыки')
def start_search(message):
    msg = bot.send_message(
        message.chat.id,
        "🔍 <b>Введите название песни:</b>",
        reply_markup=types.ForceReply()
    )
    bot.register_next_step_handler(msg, process_search_query)

def process_search_query(message):
    try:
        search_results = safe_search(message.text)
        if not search_results:
            raise Exception("Ничего не найдено")
        
        user_data[message.chat.id] = {
            'results': {vid.video_id: vid for vid in search_results}
        }
        
        markup = types.InlineKeyboardMarkup()
        for vid in search_results[:5]:
            markup.add(types.InlineKeyboardButton(
                f"{vid.title[:30]}",
                callback_data=f"select_{vid.video_id}"
            ))
        
        bot.send_message(
            message.chat.id,
            "🎵 <b>Результаты:</b>",
            reply_markup=markup
        )
    
    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"⚠️ Ошибка: {str(e)}",
            reply_markup=create_main_menu()
        )

@bot.callback_query_handler(func=lambda c: c.data.startswith('select_'))
def handle_selection(call):
    try:
        video_id = call.data.split('_')[1]
        video = user_data[call.message.chat.id]['results'][video_id]
        
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("🎶 MP3", callback_data=f"dl_{video_id}_mp3"),
            types.InlineKeyboardButton("🎥 MP4", callback_data=f"dl_{video_id}_mp4")
        )
        
        bot.send_photo(
            call.message.chat.id,
            video.thumbnail_url,
            caption=f"<b>{video.title}</b>\nВыберите формат:",
            reply_markup=markup
        )
    
    except Exception as e:
        bot.send_message(
            call.message.chat.id,
            f"⚠️ Ошибка: {str(e)}",
            reply_markup=create_main_menu()
        )

@bot.callback_query_handler(func=lambda c: c.data.startswith('dl_'))
def download_file(call):
    try:
        _, video_id, format_type = call.data.split('_')
        yt = YouTube(f"https://youtu.be/{video_id}", use_oauth=True)
        buffer = BytesIO()
        
        if format_type == "mp3":
            stream = yt.streams.filter(only_audio=True).first()
            stream.stream_to_buffer(buffer)
            buffer.seek(0)
            bot.send_audio(
                call.message.chat.id,
                buffer,
                title=yt.title,
                performer=yt.author
            )
        else:
            stream = yt.streams.filter(
                file_extension="mp4",
                progressive=True
            ).order_by('resolution').desc().first()
            stream.stream_to_buffer(buffer)
            buffer.seek(0)
            bot.send_video(
                call.message.chat.id,
                buffer,
                caption=f"<b>{yt.title}</b>"
            )
            
    except Exception as e:
        bot.send_message(
            call.message.chat.id,
            f"⚠️ Ошибка загрузки: {str(e)}",
            reply_markup=create_main_menu()
        )

# --- Вебхуки для Render ---
@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    json_str = request.stream.read().decode('utf-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "ok", 200

@app.route('/')
def index():
    return {"status": "Bot is running"}, 200

@app.route('/set_webhook')
def set_wh():
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{BOT_TOKEN}"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    return f"Webhook set to {webhook_url}", 200

@app.route('/ping')
def ping():
    return "pong", 200

# --- Запуск ---
if __name__ == '__main__':
    if os.getenv('ENVIRONMENT') == 'development':
        bot.infinity_polling()
    else:
        app.run(host='0.0.0.0', port=5000)
