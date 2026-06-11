"""
Модуль для работы с хранением пользовательских данных.
Данные сохраняются в JSON файл User_Data.json.
"""
import json
import os

DATA_FILE = "User_Data.json"


def load_user(user_id: int) -> dict:
    """
    Загружает данные пользователя из файла.
    
    Args:
        user_id: ID пользователя
    
    Returns:
        Словарь с данными пользователя или пустой словарь, если пользователь не найден
    """
    if not os.path.exists(DATA_FILE):
        return {}
    
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get(str(user_id), {})
    except (json.JSONDecodeError, IOError, KeyError):
        return {}


def save_user(user_id: int, data: dict) -> None:
    """
    Сохраняет данные пользователя в файл.
    
    Args:
        user_id: ID пользователя
        data: Словарь с данными для сохранения
    """
    # Загружаем существующие данные
    all_data = {}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                all_data = json.load(f)
        except (json.JSONDecodeError, IOError):
            all_data = {}
    
    # Обновляем данные пользователя
    all_data[str(user_id)] = data
    
    # Сохраняем обратно в файл
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
    except IOError:
        pass
