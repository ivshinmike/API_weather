"""
Основной модуль Telegram бота для получения информации о погоде.
"""
import os
import json
import logging
import hashlib
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Optional
import telebot
from telebot import types
from dotenv import load_dotenv
import weather_app as wa
import storage

load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('weather_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# Хранилище состояний пользователей (для обработки ввода)
user_states: Dict[int, Dict] = {}

# Хранилище для уведомлений
notification_check_time = {}  # {user_id: last_check_time}


def get_weather_emoji(weather_main: str) -> str:
    """Возвращает эмодзи для типа погоды"""
    emoji_map = {
        "Clear": "☀️",
        "Clouds": "☁️",
        "Rain": "🌧️",
        "Drizzle": "🌦️",
        "Thunderstorm": "⛈️",
        "Snow": "❄️",
        "Mist": "🌫️",
        "Fog": "🌫️",
        "Haze": "🌫️"
    }
    return emoji_map.get(weather_main, "🌤️")


def format_current_weather(weather_data: dict, city_name: str = None) -> str:
    """Форматирует текущую погоду для вывода"""
    if not weather_data:
        return "❌ Не удалось получить данные о погоде."
    
    main = weather_data.get("main", {})
    weather = weather_data.get("weather", [{}])[0]
    wind = weather_data.get("wind", {})
    clouds = weather_data.get("clouds", {})
    
    city = city_name or weather_data.get("name", "Неизвестно")
    temp = main.get("temp", "N/A")
    feels_like = main.get("feels_like", "N/A")
    humidity = main.get("humidity", "N/A")
    pressure = main.get("pressure", "N/A")
    description = weather.get("description", "N/A").capitalize()
    weather_main = weather.get("main", "")
    wind_speed = wind.get("speed", "N/A")
    wind_deg = wind.get("deg", "N/A")
    cloudiness = clouds.get("all", "N/A")
    
    emoji = get_weather_emoji(weather_main)
    
    text = f"{emoji} <b>Погода в {city}</b>\n\n"
    text += f"🌡️ Температура: {temp}°C\n"
    text += f"💭 Ощущается как: {feels_like}°C\n"
    text += f"💧 Влажность: {humidity}%\n"
    text += f"🌬️ Ветер: {wind_speed} м/с"
    if wind_deg != "N/A":
        text += f" ({wind_deg}°)\n"
    else:
        text += "\n"
    text += f"☁️ Облачность: {cloudiness}%\n"
    text += f"📊 Давление: {pressure} гПа\n"
    text += f"📝 Описание: {description}"
    
    return text


def format_extended_weather(weather_data: dict, air_data: dict, city_name: str = None) -> str:
    """Форматирует расширенные данные о погоде"""
    if not weather_data:
        return "❌ Не удалось получить данные о погоде."
    
    main = weather_data.get("main", {})
    weather = weather_data.get("weather", [{}])[0]
    wind = weather_data.get("wind", {})
    clouds = weather_data.get("clouds", {})
    sys = weather_data.get("sys", {})
    coord = weather_data.get("coord", {})
    
    city = city_name or weather_data.get("name", "Неизвестно")
    temp = main.get("temp", "N/A")
    feels_like = main.get("feels_like", "N/A")
    temp_min = main.get("temp_min", "N/A")
    temp_max = main.get("temp_max", "N/A")
    humidity = main.get("humidity", "N/A")
    pressure = main.get("pressure", "N/A")
    description = weather.get("description", "N/A").capitalize()
    weather_main = weather.get("main", "")
    wind_speed = wind.get("speed", "N/A")
    wind_deg = wind.get("deg", "N/A")
    cloudiness = clouds.get("all", "N/A")
    visibility = weather_data.get("visibility", "N/A")
    
    # Время восхода и заката
    sunrise = sys.get("sunrise")
    sunset = sys.get("sunset")
    sunrise_time = datetime.fromtimestamp(sunrise).strftime("%H:%M") if sunrise else "N/A"
    sunset_time = datetime.fromtimestamp(sunset).strftime("%H:%M") if sunset else "N/A"
    
    # UV индекс (если доступен)
    uvi = weather_data.get("uvi", "N/A")
    
    emoji = get_weather_emoji(weather_main)
    
    text = f"{emoji} <b>Расширенные данные: {city}</b>\n\n"
    text += f"📍 Координаты: {coord.get('lat', 'N/A')}, {coord.get('lon', 'N/A')}\n\n"
    text += f"🌡️ <b>Температура:</b>\n"
    text += f"   • Текущая: {temp}°C\n"
    text += f"   • Ощущается: {feels_like}°C\n"
    text += f"   • Минимум: {temp_min}°C\n"
    text += f"   • Максимум: {temp_max}°C\n\n"
    text += f"💧 Влажность: {humidity}%\n"
    text += f"📊 Давление: {pressure} гПа\n"
    text += f"🌬️ Ветер: {wind_speed} м/с"
    if wind_deg != "N/A":
        text += f" ({wind_deg}°)\n"
    else:
        text += "\n"
    text += f"☁️ Облачность: {cloudiness}%\n"
    if visibility != "N/A":
        text += f"👁️ Видимость: {visibility/1000:.1f} км\n"
    text += f"☀️ UV индекс: {uvi}\n"
    text += f"🌅 Восход: {sunrise_time}\n"
    text += f"🌇 Закат: {sunset_time}\n"
    text += f"📝 Описание: {description}\n"
    
    # Данные о загрязнении воздуха
    if air_data:
        air_analysis = wa.analyze_air_pollution(air_data, extended=True)
        text += f"\n🌬️ <b>Качество воздуха:</b>\n"
        text += f"   Статус: {air_analysis.get('status_ru', 'N/A')}\n"
        
        if air_analysis.get("above_norm"):
            text += f"   ⚠️ Превышения нормы:\n"
            for item in air_analysis["above_norm"][:3]:  # Показываем первые 3
                text += f"      • {item['pollutant']}: {item['value']:.2f} мкг/м³ (норма: {item['norm']})\n"
    
    return text


def format_forecast_day(forecast_list: list, day_offset: int) -> str:
    """Форматирует прогноз на конкретный день"""
    if not forecast_list:
        return "❌ Нет данных для этого дня."
    
    # Фильтруем прогнозы для нужного дня
    target_date = datetime.now().date() + timedelta(days=day_offset)
    day_forecasts = []
    
    for item in forecast_list:
        dt = datetime.fromtimestamp(item.get("dt", 0))
        if dt.date() == target_date:
            day_forecasts.append(item)
    
    if not day_forecasts:
        return f"❌ Нет данных для {target_date.strftime('%d.%m.%Y')}"
    
    # Берем средние значения и максимальные/минимальные
    temps = [item.get("main", {}).get("temp", 0) for item in day_forecasts]
    feels_like = [item.get("main", {}).get("feels_like", 0) for item in day_forecasts]
    humidity = [item.get("main", {}).get("humidity", 0) for item in day_forecasts]
    wind_speed = [item.get("wind", {}).get("speed", 0) for item in day_forecasts]
    descriptions = [item.get("weather", [{}])[0].get("description", "") for item in day_forecasts]
    
    avg_temp = sum(temps) / len(temps) if temps else 0
    avg_feels = sum(feels_like) / len(feels_like) if feels_like else 0
    avg_humidity = sum(humidity) / len(humidity) if humidity else 0
    avg_wind = sum(wind_speed) / len(wind_speed) if wind_speed else 0
    min_temp = min(temps) if temps else 0
    max_temp = max(temps) if temps else 0
    
    # Наиболее частое описание
    main_description = max(set(descriptions), key=descriptions.count) if descriptions else "N/A"
    weather_main = day_forecasts[0].get("weather", [{}])[0].get("main", "")
    emoji = get_weather_emoji(weather_main)
    
    day_name = target_date.strftime("%d.%m.%Y")
    weekday = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"][target_date.weekday()]
    
    text = f"{emoji} <b>{weekday}, {day_name}</b>\n\n"
    text += f"🌡️ Температура: {avg_temp:.1f}°C\n"
    text += f"   • Минимум: {min_temp:.1f}°C\n"
    text += f"   • Максимум: {max_temp:.1f}°C\n"
    text += f"   • Ощущается: {avg_feels:.1f}°C\n"
    text += f"💧 Влажность: {avg_humidity:.0f}%\n"
    text += f"🌬️ Ветер: {avg_wind:.1f} м/с\n"
    text += f"📝 {main_description.capitalize()}\n\n"
    text += f"<b>Прогноз по времени:</b>\n"
    
    # Показываем прогнозы по времени (каждые 3 часа)
    for item in day_forecasts[:8]:  # Максимум 8 прогнозов
        dt = datetime.fromtimestamp(item.get("dt", 0))
        time_str = dt.strftime("%H:%M")
        temp = item.get("main", {}).get("temp", "N/A")
        desc = item.get("weather", [{}])[0].get("description", "N/A").capitalize()
        text += f"   {time_str}: {temp}°C, {desc}\n"
    
    return text


def format_city_comparison(city1: str, city2: str, weather1: dict, weather2: dict) -> str:
    """Форматирует сравнение двух городов"""
    if not weather1 or not weather2:
        return "❌ Не удалось получить данные для одного из городов."
    
    main1 = weather1.get("main", {})
    main2 = weather2.get("main", {})
    weather1_desc = weather1.get("weather", [{}])[0].get("description", "N/A").capitalize()
    weather2_desc = weather2.get("weather", [{}])[0].get("description", "N/A").capitalize()
    wind1 = weather1.get("wind", {}).get("speed", "N/A")
    wind2 = weather2.get("wind", {}).get("speed", "N/A")
    
    temp1 = main1.get("temp", "N/A")
    temp2 = main2.get("temp", "N/A")
    feels1 = main1.get("feels_like", "N/A")
    feels2 = main2.get("feels_like", "N/A")
    humidity1 = main1.get("humidity", "N/A")
    humidity2 = main2.get("humidity", "N/A")
    pressure1 = main1.get("pressure", "N/A")
    pressure2 = main2.get("pressure", "N/A")
    
    text = f"📊 <b>Сравнение городов</b>\n\n"
    text += f"{'='*30}\n"
    text += f"<b>{city1}</b>          <b>{city2}</b>\n"
    text += f"{'='*30}\n"
    text += f"🌡️ Температура:\n"
    text += f"   {temp1}°C              {temp2}°C\n"
    text += f"💭 Ощущается:\n"
    text += f"   {feels1}°C              {feels2}°C\n"
    text += f"💧 Влажность:\n"
    text += f"   {humidity1}%              {humidity2}%\n"
    text += f"🌬️ Ветер:\n"
    text += f"   {wind1} м/с              {wind2} м/с\n"
    text += f"📊 Давление:\n"
    text += f"   {pressure1} гПа              {pressure2} гПа\n"
    text += f"📝 Погода:\n"
    text += f"   {weather1_desc}\n"
    text += f"   {weather2_desc}\n"
    
    # Определяем победителя по температуре
    if temp1 != "N/A" and temp2 != "N/A":
        if temp1 > temp2:
            text += f"\n🏆 В {city1} теплее на {temp1 - temp2:.1f}°C"
        elif temp2 > temp1:
            text += f"\n🏆 В {city2} теплее на {temp2 - temp1:.1f}°C"
        else:
            text += f"\n🏆 Температура одинаковая"
    
    return text


def create_main_menu() -> types.ReplyKeyboardMarkup:
    """Создает главное меню с кнопками"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        types.KeyboardButton("🌡️ Текущая погода"),
        types.KeyboardButton("📅 Прогноз на 5 дней")
    )
    keyboard.add(
        types.KeyboardButton("📍 Моя геолокация"),
        types.KeyboardButton("⚖️ Сравнить города")
    )
    keyboard.add(
        types.KeyboardButton("📊 Расширенные данные"),
        types.KeyboardButton("🔔 Уведомления")
    )
    return keyboard


def create_forecast_keyboard(selected_day: int = None) -> types.InlineKeyboardMarkup:
    """Создает inline-клавиатуру для выбора дня прогноза"""
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    
    days = ["Сегодня", "Завтра", "Через 2 дня", "Через 3 дня", "Через 4 дня"]
    for i, day in enumerate(days):
        callback_data = f"forecast_day_{i}"
        if selected_day == i:
            keyboard.add(types.InlineKeyboardButton(f"✓ {day}", callback_data=callback_data))
        else:
            keyboard.add(types.InlineKeyboardButton(day, callback_data=callback_data))
    
    if selected_day is not None:
        keyboard.add(types.InlineKeyboardButton("◀️ Назад", callback_data="forecast_back"))
    
    return keyboard


def create_notifications_keyboard(user_id: int) -> types.InlineKeyboardMarkup:
    """Создает клавиатуру для управления уведомлениями"""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    user_data = storage.load_user(user_id)
    notifications_enabled = user_data.get("notifications_enabled", False)
    
    if notifications_enabled:
        keyboard.add(types.InlineKeyboardButton("🔕 Отключить уведомления", callback_data="notif_toggle"))
    else:
        keyboard.add(types.InlineKeyboardButton("🔔 Включить уведомления", callback_data="notif_toggle"))
    
    keyboard.add(types.InlineKeyboardButton("◀️ Назад в меню", callback_data="notif_back"))
    
    return keyboard


@bot.message_handler(commands=['start'])
def handle_start(message: types.Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} запустил бота")
    user_data = storage.load_user(user_id)
    
    # Инициализируем данные пользователя, если их нет
    if not user_data:
        user_data = {
            "notifications_enabled": False,
            "location": None,
            "last_notification_check": None
        }
        storage.save_user(user_id, user_data)
        logger.info(f"Создан новый профиль для пользователя {user_id}")
    
    welcome_text = (
        "🌤️ <b>Добро пожаловать в бота погоды!</b>\n\n"
        "Выберите одну из функций:\n\n"
        "🌡️ <b>Текущая погода</b> - узнайте погоду в любом городе\n"
        "📅 <b>Прогноз на 5 дней</b> - прогноз для сохраненной геолокации\n"
        "📍 <b>Моя геолокация</b> - сохраните свое местоположение\n"
        "⚖️ <b>Сравнить города</b> - сравните погоду в двух городах\n"
        "📊 <b>Расширенные данные</b> - полная информация о погоде\n"
        "🔔 <b>Уведомления</b> - настройка погодных уведомлений"
    )
    
    bot.send_message(
        message.chat.id,
        welcome_text,
        reply_markup=create_main_menu(),
        parse_mode="HTML"
    )


@bot.message_handler(func=lambda message: message.text == "🌡️ Текущая погода")
def handle_current_weather(message: types.Message):
    """Обработчик запроса текущей погоды"""
    user_id = message.from_user.id
    user_states[user_id] = {"action": "current_weather"}
    
    bot.send_message(
        message.chat.id,
        "🌡️ Введите название города:",
        reply_markup=types.ReplyKeyboardRemove()
    )


@bot.message_handler(func=lambda message: message.text == "📅 Прогноз на 5 дней")
def handle_forecast_5days(message: types.Message):
    """Обработчик запроса прогноза на 5 дней"""
    user_id = message.from_user.id
    user_data = storage.load_user(user_id)
    
    location = user_data.get("location")
    if not location:
        logger.info(f"Пользователь {user_id} запросил прогноз без сохраненной геолокации")
        bot.send_message(
            message.chat.id,
            "📍 Для получения прогноза на 5 дней необходимо сохранить вашу геолокацию.\n\n"
            "Пожалуйста, используйте кнопку '📍 Моя геолокация' и отправьте ваше местоположение.",
            reply_markup=create_main_menu()
        )
        return
    
    lat, lon = location["lat"], location["lon"]
    forecast_list = wa.get_forecast_5d3h(lat, lon)
    
    if not forecast_list:
        bot.send_message(
            message.chat.id,
            "❌ Не удалось получить прогноз погоды.",
            reply_markup=create_main_menu()
        )
        return
    
    text = "📅 <b>Прогноз погоды на 5 дней</b>\n\nВыберите день для подробной информации:"
    
    bot.send_message(
        message.chat.id,
        text,
        reply_markup=create_forecast_keyboard(),
        parse_mode="HTML"
    )


@bot.message_handler(func=lambda message: message.text == "📍 Моя геолокация")
def handle_geolocation(message: types.Message):
    """Обработчик запроса геолокации"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton("📍 Отправить местоположение", request_location=True))
    keyboard.add(types.KeyboardButton("◀️ Назад в меню"))
    
    bot.send_message(
        message.chat.id,
        "📍 Пожалуйста, отправьте ваше местоположение:",
        reply_markup=keyboard
    )


@bot.message_handler(func=lambda message: message.text == "⚖️ Сравнить города")
def handle_compare_cities(message: types.Message):
    """Обработчик сравнения городов"""
    user_id = message.from_user.id
    user_states[user_id] = {"action": "compare_cities", "step": 1}
    
    bot.send_message(
        message.chat.id,
        "⚖️ Введите название первого города:",
        reply_markup=types.ReplyKeyboardRemove()
    )


@bot.message_handler(func=lambda message: message.text == "📊 Расширенные данные")
def handle_extended_data(message: types.Message):
    """Обработчик расширенных данных"""
    user_id = message.from_user.id
    user_states[user_id] = {"action": "extended_data"}
    
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        types.KeyboardButton("🏙️ По городу"),
        types.KeyboardButton("📍 По геолокации")
    )
    keyboard.add(types.KeyboardButton("◀️ Назад в меню"))
    
    bot.send_message(
        message.chat.id,
        "📊 Выберите способ получения расширенных данных:",
        reply_markup=keyboard
    )


@bot.message_handler(func=lambda message: message.text == "🔔 Уведомления")
def handle_notifications(message: types.Message):
    """Обработчик управления уведомлениями"""
    user_id = message.from_user.id
    user_data = storage.load_user(user_id)
    notifications_enabled = user_data.get("notifications_enabled", False)
    
    status = "включены" if notifications_enabled else "выключены"
    text = f"🔔 <b>Управление уведомлениями</b>\n\nТекущий статус: {status}\n\nБот будет проверять погоду каждые 2 часа и уведомлять о важных изменениях (например, о дожде завтра)."
    
    bot.send_message(
        message.chat.id,
        text,
        reply_markup=create_notifications_keyboard(user_id),
        parse_mode="HTML"
    )


@bot.message_handler(content_types=['location'])
def handle_location(message: types.Message):
    """Обработчик получения геолокации"""
    user_id = message.from_user.id
    location = message.location
    
    if not location:
        logger.warning(f"Пустая геолокация от пользователя {user_id}")
        bot.send_message(
            message.chat.id,
            "❌ Не удалось получить местоположение.\n\n"
            "Пожалуйста, отправьте ваше местоположение, используя кнопку '📍 Отправить местоположение'.",
            reply_markup=create_main_menu()
        )
        return
    
    logger.info(f"Получена геолокация от пользователя {user_id}: ({location.latitude}, {location.longitude})")
    
    # Сохраняем геолокацию
    user_data = storage.load_user(user_id)
    user_data["location"] = {
        "lat": location.latitude,
        "lon": location.longitude
    }
    storage.save_user(user_id, user_data)
    
    # Получаем и показываем погоду
    weather_data = wa.get_current_weather(location.latitude, location.longitude)
    if weather_data:
        city_name = weather_data.get("name", "Ваше местоположение")
        text = format_current_weather(weather_data, city_name)
        bot.send_message(
            message.chat.id,
            text,
            reply_markup=create_main_menu(),
            parse_mode="HTML"
        )
        bot.send_message(
            message.chat.id,
            "✅ Геолокация сохранена! Теперь вы можете использовать функцию '📅 Прогноз на 5 дней'.",
            reply_markup=create_main_menu()
        )
    else:
        bot.send_message(
            message.chat.id,
            "❌ Не удалось получить данные о погоде для вашего местоположения.",
            reply_markup=create_main_menu()
        )


@bot.message_handler(func=lambda message: True)
def handle_text(message: types.Message):
    """Обработчик текстовых сообщений"""
    user_id = message.from_user.id
    text = message.text.strip()
    
    # Обработка кнопки "Назад в меню"
    if text == "◀️ Назад в меню":
        handle_start(message)
        return
    
    # Проверяем состояние пользователя
    state = user_states.get(user_id, {})
    action = state.get("action")
    
    if action == "current_weather":
        # Получаем погоду по городу
        logger.info(f"Пользователь {user_id} запросил погоду для города: {text}")
        coords = wa.get_coordinates(text)
        if not coords:
            logger.warning(f"Город '{text}' не найден для пользователя {user_id}")
            bot.send_message(
                message.chat.id,
                f"❌ Город не найден.\n\n"
                f"Проверьте правильность написания названия города '{text}' и попробуйте еще раз.\n"
                f"Примеры: Москва, Санкт-Петербург, London, New York",
                reply_markup=types.ReplyKeyboardRemove()
            )
            return
        
        lat, lon = coords
        weather_data = wa.get_current_weather(lat, lon)
        
        if weather_data:
            city_name = weather_data.get("name", text)
            formatted_text = format_current_weather(weather_data, city_name)
            bot.send_message(
                message.chat.id,
                formatted_text,
                reply_markup=create_main_menu(),
                parse_mode="HTML"
            )
        else:
            bot.send_message(
                message.chat.id,
                "❌ Не удалось получить данные о погоде.",
                reply_markup=create_main_menu()
            )
        
        user_states.pop(user_id, None)
    
    elif action == "compare_cities":
        step = state.get("step", 1)
        
        if step == 1:
            # Первый город
            logger.info(f"Пользователь {user_id} ввел первый город для сравнения: {text}")
            coords1 = wa.get_coordinates(text)
            if not coords1:
                logger.warning(f"Первый город '{text}' не найден для пользователя {user_id}")
                bot.send_message(
                    message.chat.id,
                    f"❌ Город не найден.\n\n"
                    f"Проверьте правильность написания названия города '{text}' и попробуйте еще раз.\n"
                    f"Примеры: Москва, Санкт-Петербург, London, New York",
                    reply_markup=types.ReplyKeyboardRemove()
                )
                return
            
            user_states[user_id] = {
                "action": "compare_cities",
                "step": 2,
                "city1": text,
                "coords1": coords1
            }
            
            bot.send_message(
                message.chat.id,
                "⚖️ Введите название второго города:",
                reply_markup=types.ReplyKeyboardRemove()
            )
        
        elif step == 2:
            # Второй город
            city1 = state.get("city1")
            coords1 = state.get("coords1")
            
            logger.info(f"Пользователь {user_id} ввел второй город для сравнения: {text}")
            coords2 = wa.get_coordinates(text)
            if not coords2:
                logger.warning(f"Второй город '{text}' не найден для пользователя {user_id}")
                bot.send_message(
                    message.chat.id,
                    f"❌ Город не найден.\n\n"
                    f"Проверьте правильность написания названия города '{text}' и попробуйте еще раз.\n"
                    f"Примеры: Москва, Санкт-Петербург, London, New York",
                    reply_markup=types.ReplyKeyboardRemove()
                )
                return
            
            # Получаем погоду для обоих городов
            lat1, lon1 = coords1
            lat2, lon2 = coords2
            
            weather1 = wa.get_current_weather(lat1, lon1)
            weather2 = wa.get_current_weather(lat2, lon2)
            
            if weather1 and weather2:
                city1_name = weather1.get("name", city1)
                city2_name = weather2.get("name", text)
                comparison_text = format_city_comparison(city1_name, city2_name, weather1, weather2)
                bot.send_message(
                    message.chat.id,
                    comparison_text,
                    reply_markup=create_main_menu(),
                    parse_mode="HTML"
                )
            else:
                bot.send_message(
                    message.chat.id,
                    "❌ Не удалось получить данные о погоде для одного из городов.",
                    reply_markup=create_main_menu()
                )
            
            user_states.pop(user_id, None)
    
    elif action == "extended_data":
        if text == "🏙️ По городу":
            user_states[user_id] = {"action": "extended_data_city"}
            bot.send_message(
                message.chat.id,
                "🏙️ Введите название города:",
                reply_markup=types.ReplyKeyboardRemove()
            )
        elif text == "📍 По геолокации":
            user_data = storage.load_user(user_id)
            location = user_data.get("location")
            
            if not location:
                logger.info(f"Пользователь {user_id} запросил расширенные данные без сохраненной геолокации")
                bot.send_message(
                    message.chat.id,
                    "📍 Для получения расширенных данных по геолокации необходимо сохранить ваше местоположение.\n\n"
                    "Пожалуйста, используйте кнопку '📍 Моя геолокация' и отправьте ваше местоположение.",
                    reply_markup=create_main_menu()
                )
                user_states.pop(user_id, None)
                return
            
            lat, lon = location["lat"], location["lon"]
            weather_data = wa.get_current_weather(lat, lon)
            air_data = wa.get_air_pollution(lat, lon)
            
            if weather_data:
                city_name = weather_data.get("name", "Ваше местоположение")
                extended_text = format_extended_weather(weather_data, air_data, city_name)
                bot.send_message(
                    message.chat.id,
                    extended_text,
                    reply_markup=create_main_menu(),
                    parse_mode="HTML"
                )
            else:
                bot.send_message(
                    message.chat.id,
                    "❌ Не удалось получить данные о погоде.",
                    reply_markup=create_main_menu()
                )
            
            user_states.pop(user_id, None)
    
    elif action == "extended_data_city":
        logger.info(f"Пользователь {user_id} запросил расширенные данные для города: {text}")
        coords = wa.get_coordinates(text)
        if not coords:
            logger.warning(f"Город '{text}' не найден для расширенных данных (пользователь {user_id})")
            bot.send_message(
                message.chat.id,
                f"❌ Город не найден.\n\n"
                f"Проверьте правильность написания названия города '{text}' и попробуйте еще раз.\n"
                f"Примеры: Москва, Санкт-Петербург, London, New York",
                reply_markup=types.ReplyKeyboardRemove()
            )
            return
        
        lat, lon = coords
        weather_data = wa.get_current_weather(lat, lon)
        air_data = wa.get_air_pollution(lat, lon)
        
        if weather_data:
            city_name = weather_data.get("name", text)
            extended_text = format_extended_weather(weather_data, air_data, city_name)
            bot.send_message(
                message.chat.id,
                extended_text,
                reply_markup=create_main_menu(),
                parse_mode="HTML"
            )
        else:
            bot.send_message(
                message.chat.id,
                "❌ Не удалось получить данные о погоде.",
                reply_markup=create_main_menu()
            )
        
        user_states.pop(user_id, None)
    
    else:
        # Неизвестная команда
        bot.send_message(
            message.chat.id,
            "❓ Не понимаю эту команду. Используйте меню для выбора функции.",
            reply_markup=create_main_menu()
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith("forecast_"))
def handle_forecast_callback(call: types.CallbackQuery):
    """Обработчик callback для прогноза на 5 дней"""
    user_id = call.from_user.id
    user_data = storage.load_user(user_id)
    location = user_data.get("location")
    
    if not location:
        logger.info(f"Пользователь {user_id} попытался получить прогноз без сохраненной геолокации")
        bot.answer_callback_query(call.id, "❌ Сначала сохраните геолокацию")
        bot.send_message(
            call.message.chat.id,
            "📍 Для получения прогноза на 5 дней необходимо сохранить вашу геолокацию.\n\n"
            "Пожалуйста, используйте кнопку '📍 Моя геолокация' и отправьте ваше местоположение.",
            reply_markup=create_main_menu()
        )
        return
    
    if call.data == "forecast_back":
        # Возврат к списку дней
        forecast_list = wa.get_forecast_5d3h(location["lat"], location["lon"])
        if forecast_list:
            text = "📅 <b>Прогноз погоды на 5 дней</b>\n\nВыберите день для подробной информации:"
            bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=create_forecast_keyboard(),
                parse_mode="HTML"
            )
        return
    
    if call.data.startswith("forecast_day_"):
        day_offset = int(call.data.split("_")[-1])
        forecast_list = wa.get_forecast_5d3h(location["lat"], location["lon"])
        
        if forecast_list:
            day_text = format_forecast_day(forecast_list, day_offset)
            bot.edit_message_text(
                day_text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=create_forecast_keyboard(selected_day=day_offset),
                parse_mode="HTML"
            )
        else:
            bot.answer_callback_query(call.id, "❌ Не удалось получить прогноз")
    
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("notif_"))
def handle_notifications_callback(call: types.CallbackQuery):
    """Обработчик callback для уведомлений"""
    user_id = call.from_user.id
    
    if call.data == "notif_toggle":
        user_data = storage.load_user(user_id)
        notifications_enabled = user_data.get("notifications_enabled", False)
        user_data["notifications_enabled"] = not notifications_enabled
        storage.save_user(user_id, user_data)
        
        status = "включены" if user_data["notifications_enabled"] else "выключены"
        text = f"🔔 <b>Управление уведомлениями</b>\n\nТекущий статус: {status}\n\nБот будет проверять погоду каждые 2 часа и уведомлять о важных изменениях (например, о дожде завтра)."
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=create_notifications_keyboard(user_id),
            parse_mode="HTML"
        )
        bot.answer_callback_query(call.id, f"Уведомления {status}")
    
    elif call.data == "notif_back":
        handle_start(call.message)
        bot.answer_callback_query(call.id)


@bot.inline_handler(func=lambda query: len(query.query) > 0)
def handle_inline_query(query: types.InlineQuery):
    """Обработчик inline-запросов для поиска погоды по городу"""
    query_text = query.query.strip()
    
    if not query_text or len(query_text) < 2:
        # Минимум 2 символа для поиска
        bot.answer_inline_query(query.id, [])
        return
    
    logger.info(f"Inline-запрос от пользователя {query.from_user.id}: {query_text}")
    
    # Получаем координаты города
    coords = wa.get_coordinates(query_text)
    
    if not coords:
        # Если город не найден, показываем сообщение об ошибке
        result = types.InlineQueryResultArticle(
            id="not_found",
            title=f"❌ Город '{query_text}' не найден",
            description="Попробуйте другое название",
            input_message_content=types.InputTextMessageContent(
                message_text=f"❌ Город '{query_text}' не найден. Попробуйте другое название."
            )
        )
        bot.answer_inline_query(query.id, [result], cache_time=60)
        return
    
    lat, lon = coords
    
    # Получаем текущую погоду
    weather_data = wa.get_current_weather(lat, lon)
    
    if not weather_data:
        result = types.InlineQueryResultArticle(
            id="error",
            title="❌ Ошибка получения данных",
            description="Не удалось получить данные о погоде",
            input_message_content=types.InputTextMessageContent(
                message_text="❌ Не удалось получить данные о погоде."
            )
        )
        bot.answer_inline_query(query.id, [result], cache_time=60)
        return
    
    # Форматируем данные для карточки
    main = weather_data.get("main", {})
    weather = weather_data.get("weather", [{}])[0]
    wind = weather_data.get("wind", {})
    
    city_name = weather_data.get("name", query_text)
    temp = main.get("temp", "N/A")
    feels_like = main.get("feels_like", "N/A")
    humidity = main.get("humidity", "N/A")
    description = weather.get("description", "N/A").capitalize()
    weather_main = weather.get("main", "")
    wind_speed = wind.get("speed", "N/A")
    
    emoji = get_weather_emoji(weather_main)
    
    # Формируем текст сообщения
    message_text = (
        f"{emoji} <b>Погода в {city_name}</b>\n\n"
        f"🌡️ Температура: {temp}°C\n"
        f"💭 Ощущается как: {feels_like}°C\n"
        f"💧 Влажность: {humidity}%\n"
        f"🌬️ Ветер: {wind_speed} м/с\n"
        f"📝 {description}"
    )
    
    # Формируем ссылку на прогноз (используем хеш координат для более короткого callback_data)
    coords_hash = hashlib.md5(f"{lat}_{lon}".encode()).hexdigest()[:8]
    
    # Сохраняем координаты во временный кэш для callback
    inline_coords_cache[coords_hash] = (lat, lon, city_name)
    
    # Создаем inline-результат с карточкой
    result = types.InlineQueryResultArticle(
        id=f"weather_{coords_hash}",
        title=f"{emoji} {city_name}: {temp}°C",
        description=f"{description} | Ощущается: {feels_like}°C",
        thumb_url=None,
        input_message_content=types.InputTextMessageContent(
            message_text=message_text,
            parse_mode="HTML"
        ),
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="📅 Прогноз на 5 дней",
                        callback_data=f"if_{coords_hash}"
                    )
                ],
                [
                    types.InlineKeyboardButton(
                        text="📊 Расширенные данные",
                        callback_data=f"ie_{coords_hash}"
                    )
                ]
            ]
        )
    )
    
    bot.answer_inline_query(query.id, [result], cache_time=300)  # Кэш 5 минут


# Хранилище для координат из inline-запросов (временное, для callback)
inline_coords_cache = {}  # {hash: (lat, lon, city_name)}


@bot.callback_query_handler(func=lambda call: call.data.startswith("if_") or call.data.startswith("ie_"))
def handle_inline_callback(call: types.CallbackQuery):
    """Обработчик callback для inline-результатов"""
    user_id = call.from_user.id
    data = call.data
    
    if data.startswith("if_"):
        # Прогноз на 5 дней
        coords_hash = data[3:]  # Убираем префикс "if_"
        
        # Получаем координаты из кэша или из сообщения
        if coords_hash in inline_coords_cache:
            lat, lon, city_name = inline_coords_cache[coords_hash]
        else:
            # Пытаемся извлечь координаты из текста сообщения
            # Если не найдены, просим пользователя использовать бота
            bot.answer_callback_query(
                call.id, 
                "💡 Для прогноза используйте бота напрямую",
                show_alert=False
            )
            return
        
        forecast_list = wa.get_forecast_5d3h(lat, lon)
        
        if forecast_list:
            # Формируем краткий прогноз
            text = f"📅 <b>Прогноз погоды на 5 дней: {city_name}</b>\n\n"
            
            # Группируем по дням
            days_forecast = defaultdict(list)
            
            for item in forecast_list[:40]:  # Берем первые 40 записей (5 дней * 8 прогнозов)
                dt = datetime.fromtimestamp(item.get("dt", 0))
                day_key = dt.date()
                days_forecast[day_key].append(item)
            
            # Показываем прогноз по дням
            for i, (day, items) in enumerate(list(days_forecast.items())[:5]):
                if i == 0:
                    day_name = "Сегодня"
                elif i == 1:
                    day_name = "Завтра"
                else:
                    weekday = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][day.weekday()]
                    day_name = f"{weekday}, {day.strftime('%d.%m')}"
                
                temps = [item.get("main", {}).get("temp", 0) for item in items]
                avg_temp = sum(temps) / len(temps) if temps else 0
                min_temp = min(temps) if temps else 0
                max_temp = max(temps) if temps else 0
                desc = items[0].get("weather", [{}])[0].get("description", "N/A").capitalize()
                
                text += f"<b>{day_name}</b>: {avg_temp:.0f}°C ({min_temp:.0f}°/{max_temp:.0f}°) - {desc}\n"
            
            text += f"\n💡 Для детального прогноза используйте бота напрямую"
            
            bot.answer_callback_query(call.id)
            bot.send_message(
                call.message.chat.id,
                text,
                parse_mode="HTML"
            )
        else:
            bot.answer_callback_query(call.id, "❌ Не удалось получить прогноз")
    
    elif data.startswith("ie_"):
        # Расширенные данные
        coords_hash = data[3:]  # Убираем префикс "ie_"
        
        if coords_hash in inline_coords_cache:
            lat, lon, city_name = inline_coords_cache[coords_hash]
        else:
            bot.answer_callback_query(
                call.id, 
                "💡 Для расширенных данных используйте бота напрямую",
                show_alert=False
            )
            return
        
        weather_data = wa.get_current_weather(lat, lon)
        air_data = wa.get_air_pollution(lat, lon)
        
        if weather_data:
            extended_text = format_extended_weather(weather_data, air_data, city_name)
            
            bot.answer_callback_query(call.id)
            bot.send_message(
                call.message.chat.id,
                extended_text,
                parse_mode="HTML"
            )
        else:
            bot.answer_callback_query(call.id, "❌ Не удалось получить данные")


def check_notifications():
    """Проверяет уведомления для всех пользователей (вызывается периодически)"""
    # Загружаем всех пользователей
    if not os.path.exists("User_Data.json"):
        return
    
    try:
        with open("User_Data.json", "r", encoding="utf-8") as f:
            all_data = json.load(f)
    except:
        return
    
    current_time = time.time()
    
    for user_id_str, user_data in all_data.items():
        if not user_data.get("notifications_enabled", False):
            continue
        
        user_id = int(user_id_str)
        location = user_data.get("location")
        if not location:
            continue
        
        last_check = user_data.get("last_notification_check")
        # Проверяем каждые 2 часа (7200 секунд)
        if last_check and (current_time - last_check) < 7200:
            continue
        
        # Получаем прогноз
        lat, lon = location["lat"], location["lon"]
        forecast_list = wa.get_forecast_5d3h(lat, lon)
        current_weather = wa.get_current_weather(lat, lon)
        
        if not forecast_list or not current_weather:
            continue
        
        # Проверяем, будет ли завтра дождь
        tomorrow = datetime.now().date() + timedelta(days=1)
        tomorrow_forecasts = []
        
        for item in forecast_list:
            dt = datetime.fromtimestamp(item.get("dt", 0))
            if dt.date() == tomorrow:
                tomorrow_forecasts.append(item)
        
        # Проверяем на дождь
        has_rain_tomorrow = False
        for item in tomorrow_forecasts:
            weather = item.get("weather", [{}])[0]
            main = weather.get("main", "").lower()
            if main in ["rain", "drizzle", "thunderstorm"]:
                has_rain_tomorrow = True
                break
        
        if has_rain_tomorrow:
            try:
                bot.send_message(
                    user_id,
                    "🌧️ <b>Погодное уведомление</b>\n\n"
                    "⚠️ Завтра ожидается дождь! Не забудьте взять зонт.",
                    parse_mode="HTML"
                )
            except:
                pass
        
        # Обновляем время последней проверки
        user_data["last_notification_check"] = current_time
        storage.save_user(user_id, user_data)


def notification_worker():
    """Рабочий поток для проверки уведомлений"""
    while True:
        try:
            check_notifications()
        except Exception as e:
            print(f"Ошибка при проверке уведомлений: {e}")
        time.sleep(300)  # Проверяем каждые 5 минут


# Запускаем поток для уведомлений
notification_thread = threading.Thread(target=notification_worker, daemon=True)
notification_thread.start()


if __name__ == "__main__":
    logger.info("Бот запущен...")
    print("Бот запущен...")
    try:
        bot.infinity_polling(none_stop=True)
    except Exception as e:
        logger.error(f"Критическая ошибка бота: {e}", exc_info=True)
        raise
