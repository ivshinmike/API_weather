"""
Модуль для работы с OpenWeather API.
Предоставляет функции для получения координат, текущей погоды,
прогноза и данных о загрязнении воздуха.
"""
import os
import json
import time
import logging
import hashlib
import requests
from typing import Tuple, Optional, Any
from pathlib import Path
from dotenv import load_dotenv

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

OW_API_KEY = os.getenv("OW_API_KEY")
BASE_URL = "https://api.openweathermap.org"

# Настройки кэша
CACHE_DIR = Path(".cache")
CACHE_TTL = 600  # 10 минут в секундах

# Создаем директорию кэша, если её нет
CACHE_DIR.mkdir(exist_ok=True)


def get_cache_key(lat: Optional[float] = None, lon: Optional[float] = None, 
                  endpoint: str = "", city: Optional[str] = None) -> str:
    """
    Генерирует ключ кэша на основе параметров.
    
    Args:
        lat: Широта
        lon: Долгота
        endpoint: Название эндпоинта
        city: Название города (для get_coordinates)
    
    Returns:
        Имя файла кэша
    """
    if city:
        # Для get_coordinates используем хеш названия города
        city_hash = hashlib.md5(city.lower().encode('utf-8')).hexdigest()[:8]
        return f"city_{city_hash}_{endpoint}.json"
    elif lat is not None and lon is not None:
        # Округляем координаты до 4 знаков для группировки близких точек
        lat_rounded = round(lat, 4)
        lon_rounded = round(lon, 4)
        return f"{lat_rounded}_{lon_rounded}_{endpoint}.json"
    else:
        return f"{endpoint}.json"


def get_cache(cache_key: str) -> Optional[Any]:
    """
    Получает данные из кэша, если они не устарели.
    
    Args:
        cache_key: Ключ кэша (имя файла)
    
    Returns:
        Данные из кэша или None, если кэш отсутствует или устарел
    """
    cache_file = CACHE_DIR / cache_key
    
    if not cache_file.exists():
        return None
    
    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            cache_data = json.load(f)
        
        timestamp = cache_data.get("timestamp", 0)
        current_time = time.time()
        
        # Проверяем, не устарел ли кэш
        if current_time - timestamp > CACHE_TTL:
            logger.debug(f"Кэш для {cache_key} устарел, удаляем")
            cache_file.unlink()
            return None
        
        logger.info(f"Данные получены из кэша: {cache_key}")
        return cache_data.get("data")
    
    except (json.JSONDecodeError, IOError, KeyError) as e:
        logger.warning(f"Ошибка при чтении кэша {cache_key}: {e}")
        # Удаляем поврежденный файл кэша
        try:
            cache_file.unlink()
        except:
            pass
        return None


def set_cache(cache_key: str, data: Any) -> None:
    """
    Сохраняет данные в кэш.
    
    Args:
        cache_key: Ключ кэша (имя файла)
        data: Данные для сохранения
    """
    cache_file = CACHE_DIR / cache_key
    
    try:
        cache_data = {
            "timestamp": time.time(),
            "data": data
        }
        
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False)
        
        logger.debug(f"Данные сохранены в кэш: {cache_key}")
    
    except IOError as e:
        logger.warning(f"Ошибка при сохранении кэша {cache_key}: {e}")


def get_coordinates(city: str, limit: int = 1) -> Tuple[float, float] | None:
    """
    Получает координаты города через OpenWeather Geocoding API.
    
    Args:
        city: Название города
        limit: Максимальное количество результатов (по умолчанию 1)
    
    Returns:
        Кортеж (широта, долгота) или None в случае ошибки
    """
    if not OW_API_KEY:
        logger.error("OW_API_KEY не установлен")
        return None
    
    # Проверяем кэш
    cache_key = get_cache_key(city=city, endpoint="coordinates")
    cached_data = get_cache(cache_key)
    if cached_data is not None:
        lat = cached_data.get("lat")
        lon = cached_data.get("lon")
        if lat is not None and lon is not None:
            return (float(lat), float(lon))
    
    url = f"{BASE_URL}/geo/1.0/direct"
    params = {
        "q": city,
        "limit": limit,
        "appid": OW_API_KEY,
        "lang": "ru"
    }
    
    # Retry логика для rate limit (429)
    retry_delays = [1, 2, 4]  # Паузы в секундах
    last_exception = None
    
    for attempt in range(len(retry_delays) + 1):
        try:
            response = requests.get(url, params=params, timeout=10)
            
            # Обработка rate limit
            if response.status_code == 429:
                if attempt < len(retry_delays):
                    delay = retry_delays[attempt]
                    logger.warning(f"Rate limit (429) при получении координат для '{city}'. Попытка {attempt + 1}/{len(retry_delays) + 1}. Ожидание {delay}с...")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"Rate limit (429) после всех попыток для города '{city}'")
                    return None
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    lat = data[0].get("lat")
                    lon = data[0].get("lon")
                    if lat is not None and lon is not None:
                        logger.info(f"Координаты для '{city}': ({lat}, {lon})")
                        # Сохраняем в кэш
                        set_cache(cache_key, {"lat": lat, "lon": lon})
                        return (float(lat), float(lon))
                else:
                    logger.info(f"Город '{city}' не найден")
                    return None
            
            # Другие ошибки HTTP
            if attempt < len(retry_delays):
                delay = retry_delays[attempt]
                logger.warning(f"HTTP {response.status_code} при получении координат для '{city}'. Попытка {attempt + 1}/{len(retry_delays) + 1}. Ожидание {delay}с...")
                time.sleep(delay)
                continue
            else:
                logger.error(f"HTTP {response.status_code} при получении координат для '{city}'")
                return None
        
        except requests.exceptions.RequestException as e:
            last_exception = e
            if attempt < len(retry_delays):
                delay = retry_delays[attempt]
                logger.warning(f"Ошибка запроса при получении координат для '{city}': {e}. Попытка {attempt + 1}/{len(retry_delays) + 1}. Ожидание {delay}с...")
                time.sleep(delay)
                continue
            else:
                logger.error(f"Ошибка запроса при получении координат для '{city}': {e}")
                return None
        except (KeyError, ValueError, IndexError) as e:
            logger.error(f"Ошибка парсинга данных для города '{city}': {e}")
            return None
    
    return None


def get_current_weather(lat: float, lon: float) -> dict:
    """
    Получает текущую погоду по координатам.
    
    Args:
        lat: Широта
        lon: Долгота
    
    Returns:
        Словарь с данными о погоде или пустой словарь в случае ошибки
    """
    if not OW_API_KEY:
        logger.error("OW_API_KEY не установлен")
        return {}
    
    # Проверяем кэш
    cache_key = get_cache_key(lat=lat, lon=lon, endpoint="current_weather")
    cached_data = get_cache(cache_key)
    if cached_data is not None:
        return cached_data
    
    url = f"{BASE_URL}/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": OW_API_KEY,
        "units": "metric",
        "lang": "ru"
    }
    
    # Retry логика для rate limit (429)
    retry_delays = [1, 2, 4]  # Паузы в секундах
    
    for attempt in range(len(retry_delays) + 1):
        try:
            response = requests.get(url, params=params, timeout=10)
            
            # Обработка rate limit
            if response.status_code == 429:
                if attempt < len(retry_delays):
                    delay = retry_delays[attempt]
                    logger.warning(f"Rate limit (429) при получении текущей погоды для ({lat}, {lon}). Попытка {attempt + 1}/{len(retry_delays) + 1}. Ожидание {delay}с...")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"Rate limit (429) после всех попыток для координат ({lat}, {lon})")
                    return {}
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Получена текущая погода для координат ({lat}, {lon})")
                # Сохраняем в кэш
                set_cache(cache_key, data)
                return data
            
            # Другие ошибки HTTP
            if attempt < len(retry_delays):
                delay = retry_delays[attempt]
                logger.warning(f"HTTP {response.status_code} при получении текущей погоды для ({lat}, {lon}). Попытка {attempt + 1}/{len(retry_delays) + 1}. Ожидание {delay}с...")
                time.sleep(delay)
                continue
            else:
                logger.error(f"HTTP {response.status_code} при получении текущей погоды для ({lat}, {lon})")
                return {}
        
        except requests.exceptions.RequestException as e:
            if attempt < len(retry_delays):
                delay = retry_delays[attempt]
                logger.warning(f"Ошибка запроса при получении текущей погоды для ({lat}, {lon}): {e}. Попытка {attempt + 1}/{len(retry_delays) + 1}. Ожидание {delay}с...")
                time.sleep(delay)
                continue
            else:
                logger.error(f"Ошибка запроса при получении текущей погоды для ({lat}, {lon}): {e}")
                return {}
        except (ValueError, KeyError) as e:
            logger.error(f"Ошибка парсинга данных о текущей погоде для ({lat}, {lon}): {e}")
            return {}
    
    return {}


def get_forecast_5d3h(lat: float, lon: float) -> list[dict]:
    """
    Получает 5-дневный прогноз погоды с шагом 3 часа.
    
    Args:
        lat: Широта
        lon: Долгота
    
    Returns:
        Список словарей с прогнозом или пустой список в случае ошибки
    """
    if not OW_API_KEY:
        logger.error("OW_API_KEY не установлен")
        return []
    
    # Проверяем кэш
    cache_key = get_cache_key(lat=lat, lon=lon, endpoint="forecast")
    cached_data = get_cache(cache_key)
    if cached_data is not None:
        return cached_data
    
    url = f"{BASE_URL}/data/2.5/forecast"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": OW_API_KEY,
        "units": "metric",
        "lang": "ru"
    }
    
    # Retry логика для rate limit (429)
    retry_delays = [1, 2, 4]  # Паузы в секундах
    
    for attempt in range(len(retry_delays) + 1):
        try:
            response = requests.get(url, params=params, timeout=10)
            
            # Обработка rate limit
            if response.status_code == 429:
                if attempt < len(retry_delays):
                    delay = retry_delays[attempt]
                    logger.warning(f"Rate limit (429) при получении прогноза для ({lat}, {lon}). Попытка {attempt + 1}/{len(retry_delays) + 1}. Ожидание {delay}с...")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"Rate limit (429) после всех попыток для прогноза ({lat}, {lon})")
                    return []
            
            if response.status_code == 200:
                data = response.json()
                if "list" in data:
                    forecast_list = data["list"]
                    logger.info(f"Получен прогноз на 5 дней для координат ({lat}, {lon})")
                    # Сохраняем в кэш
                    set_cache(cache_key, forecast_list)
                    return forecast_list
                else:
                    logger.warning(f"Нет данных 'list' в ответе для прогноза ({lat}, {lon})")
                    return []
            
            # Другие ошибки HTTP
            if attempt < len(retry_delays):
                delay = retry_delays[attempt]
                logger.warning(f"HTTP {response.status_code} при получении прогноза для ({lat}, {lon}). Попытка {attempt + 1}/{len(retry_delays) + 1}. Ожидание {delay}с...")
                time.sleep(delay)
                continue
            else:
                logger.error(f"HTTP {response.status_code} при получении прогноза для ({lat}, {lon})")
                return []
        
        except requests.exceptions.RequestException as e:
            if attempt < len(retry_delays):
                delay = retry_delays[attempt]
                logger.warning(f"Ошибка запроса при получении прогноза для ({lat}, {lon}): {e}. Попытка {attempt + 1}/{len(retry_delays) + 1}. Ожидание {delay}с...")
                time.sleep(delay)
                continue
            else:
                logger.error(f"Ошибка запроса при получении прогноза для ({lat}, {lon}): {e}")
                return []
        except (ValueError, KeyError) as e:
            logger.error(f"Ошибка парсинга данных прогноза для ({lat}, {lon}): {e}")
            return []
    
    return []


def get_air_pollution(lat: float, lon: float) -> dict:
    """
    Получает данные о загрязнении воздуха по координатам.
    
    Args:
        lat: Широта
        lon: Долгота
    
    Returns:
        Словарь с данными о загрязнении или пустой словарь в случае ошибки
    """
    if not OW_API_KEY:
        logger.error("OW_API_KEY не установлен")
        return {}
    
    # Проверяем кэш
    cache_key = get_cache_key(lat=lat, lon=lon, endpoint="air_pollution")
    cached_data = get_cache(cache_key)
    if cached_data is not None:
        return cached_data
    
    url = f"{BASE_URL}/data/2.5/air_pollution"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": OW_API_KEY
    }
    
    # Retry логика для rate limit (429)
    retry_delays = [1, 2, 4]  # Паузы в секундах
    
    for attempt in range(len(retry_delays) + 1):
        try:
            response = requests.get(url, params=params, timeout=10)
            
            # Обработка rate limit
            if response.status_code == 429:
                if attempt < len(retry_delays):
                    delay = retry_delays[attempt]
                    logger.warning(f"Rate limit (429) при получении загрязнения воздуха для ({lat}, {lon}). Попытка {attempt + 1}/{len(retry_delays) + 1}. Ожидание {delay}с...")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"Rate limit (429) после всех попыток для загрязнения воздуха ({lat}, {lon})")
                    return {}
            
            if response.status_code == 200:
                data = response.json()
                if "list" in data and len(data["list"]) > 0:
                    air_data = data["list"][0].get("components", {})
                    logger.info(f"Получены данные о загрязнении воздуха для координат ({lat}, {lon})")
                    # Сохраняем в кэш
                    set_cache(cache_key, air_data)
                    return air_data
                else:
                    logger.warning(f"Нет данных о загрязнении воздуха для ({lat}, {lon})")
                    return {}
            
            # Другие ошибки HTTP
            if attempt < len(retry_delays):
                delay = retry_delays[attempt]
                logger.warning(f"HTTP {response.status_code} при получении загрязнения воздуха для ({lat}, {lon}). Попытка {attempt + 1}/{len(retry_delays) + 1}. Ожидание {delay}с...")
                time.sleep(delay)
                continue
            else:
                logger.error(f"HTTP {response.status_code} при получении загрязнения воздуха для ({lat}, {lon})")
                return {}
        
        except requests.exceptions.RequestException as e:
            if attempt < len(retry_delays):
                delay = retry_delays[attempt]
                logger.warning(f"Ошибка запроса при получении загрязнения воздуха для ({lat}, {lon}): {e}. Попытка {attempt + 1}/{len(retry_delays) + 1}. Ожидание {delay}с...")
                time.sleep(delay)
                continue
            else:
                logger.error(f"Ошибка запроса при получении загрязнения воздуха для ({lat}, {lon}): {e}")
                return {}
        except (ValueError, KeyError, IndexError) as e:
            logger.error(f"Ошибка парсинга данных о загрязнении воздуха для ({lat}, {lon}): {e}")
            return {}
    
    return {}


def analyze_air_pollution(components: dict, extended: bool = False) -> dict:
    """
    Анализирует данные о загрязнении воздуха и возвращает сводный статус.
    Соответствует стандартной таблице оценки качества воздуха.
    
    Args:
        components: Словарь с компонентами загрязнения (co, no, no2, o3, so2, pm2_5, pm10, nh3)
        extended: Если True, возвращает расширенную информацию с превышениями нормы
    
    Returns:
        Словарь со статусом и деталями загрязнения
    """
    if not components:
        return {
            "status": "unknown",
            "index": 0,
            "message": "Данные о загрязнении недоступны"
        }
    
    # Пороговые значения согласно таблице (мкг/м³)
    # Формат: [good_max, fair_max, moderate_max, poor_max, very_poor_min]
    thresholds = {
        "so2": [20, 80, 250, 350, 350],      # SO₂
        "no2": [40, 70, 150, 200, 200],       # NO₂
        "pm10": [20, 50, 100, 200, 200],     # PM₁₀
        "pm2_5": [10, 25, 50, 75, 75],        # PM₂.₅
        "o3": [60, 100, 140, 180, 180],       # O₃
        "co": [4400, 9400, 12400, 15400, 15400]  # CO
    }
    
    # Названия загрязнителей для вывода (ASCII-совместимые)
    pollutant_names = {
        "so2": "SO2 (Диоксид серы)",
        "no2": "NO2 (Диоксид азота)",
        "pm10": "PM10 (Частицы до 10 мкм)",
        "pm2_5": "PM2.5 (Частицы до 2.5 мкм)",
        "o3": "O3 (Озон)",
        "co": "CO (Оксид углерода)"
    }
    
    # Нормы (верхняя граница "Good")
    norms = {
        "so2": 20,
        "no2": 40,
        "pm10": 20,
        "pm2_5": 10,
        "o3": 60,
        "co": 4400
    }
    
    pollutant_indices = []
    details = {}
    above_norm = []
    below_norm = []
    
    for key, value in components.items():
        if key in thresholds and isinstance(value, (int, float)):
            thresh = thresholds[key]
            pollutant_name = pollutant_names.get(key, key.upper())
            norm = norms.get(key, 0)
            
            # Определяем индекс качества для данного загрязнителя
            # Согласно таблице: Good [0; a), Fair [a; b), Moderate [b; c), Poor [c; d), Very Poor >= d или > d
            if value < thresh[0]:  # Good: [0; good_max)
                index = 1
                status = "good"
                status_ru = "Хорошее"
            elif value < thresh[1]:  # Fair: [good_max; fair_max)
                index = 2
                status = "fair"
                status_ru = "Удовлетворительное"
            elif value < thresh[2]:  # Moderate: [fair_max; moderate_max)
                index = 3
                status = "moderate"
                status_ru = "Умеренное"
            elif value < thresh[3]:  # Poor: [moderate_max; poor_max)
                index = 4
                status = "poor"
                status_ru = "Плохое"
            else:  # Very Poor: >= poor_max (для некоторых > poor_max, но используем >= для универсальности)
                index = 5
                status = "very_poor"
                status_ru = "Очень плохое"
            
            pollutant_indices.append(index)
            
            # Проверяем превышение нормы
            if value >= norm:
                above_norm.append({
                    "pollutant": pollutant_name,
                    "key": key,
                    "value": value,
                    "norm": norm,
                    "excess": round(value - norm, 2),
                    "index": index,
                    "status": status_ru
                })
            else:
                below_norm.append({
                    "pollutant": pollutant_name,
                    "key": key,
                    "value": value,
                    "norm": norm,
                    "index": index,
                    "status": status_ru
                })
            
            if extended:
                details[key] = {
                    "name": pollutant_name,
                    "value": value,
                    "index": index,
                    "status": status,
                    "status_ru": status_ru,
                    "norm": norm,
                    "above_norm": value >= norm,
                    "thresholds": {
                        "good_max": thresh[0],
                        "fair_max": thresh[1],
                        "moderate_max": thresh[2],
                        "poor_max": thresh[3],
                        "very_poor_min": thresh[4]
                    }
                }
    
    # Определяем общий индекс качества воздуха (берем максимальный)
    if not pollutant_indices:
        overall_index = 0
        overall_status = "unknown"
        overall_status_ru = "Неизвестно"
    else:
        overall_index = max(pollutant_indices)
        
        if overall_index == 1:
            overall_status = "good"
            overall_status_ru = "Хорошее"
        elif overall_index == 2:
            overall_status = "fair"
            overall_status_ru = "Удовлетворительное"
        elif overall_index == 3:
            overall_status = "moderate"
            overall_status_ru = "Умеренное"
        elif overall_index == 4:
            overall_status = "poor"
            overall_status_ru = "Плохое"
        else:
            overall_status = "very_poor"
            overall_status_ru = "Очень плохое"
    
    status_messages = {
        "good": "Хорошее качество воздуха",
        "fair": "Удовлетворительное качество воздуха",
        "moderate": "Умеренное загрязнение",
        "poor": "Плохое качество воздуха",
        "very_poor": "Очень плохое качество воздуха",
        "unknown": "Неизвестно"
    }
    
    result = {
        "status": overall_status,
        "status_ru": overall_status_ru,
        "index": overall_index,
        "message": status_messages.get(overall_status, "Неизвестно")
    }
    
    if extended:
        result["details"] = details
        result["components"] = components
        result["above_norm"] = above_norm
        result["below_norm"] = below_norm
        result["summary"] = {
            "total_pollutants": len(details),
            "above_norm_count": len(above_norm),
            "below_norm_count": len(below_norm),
            "worst_pollutant": max(above_norm, key=lambda x: x["index"], default=None) if above_norm else None
        }
    
    return result


    