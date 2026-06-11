# Weather Bot

Telegram бот для получения информации о погоде через OpenWeather API.

## Структура проекта

```
API_weather/
├── bot.py              # Основной модуль Telegram бота
├── weather_app.py      # Модуль для работы с OpenWeather API
├── storage.py          # Модуль для работы с пользовательскими данными
├── requirements.txt    # Зависимости проекта
├── .gitignore          # Игнорируемые файлы
├── .env.example        # Пример файла с переменными окружения
├── User_Data.json      # Файл для хранения данных пользователей
└── README.md           # Документация проекта
```

## Установка

1. Клонируйте репозиторий или создайте проект
2. Создайте виртуальное окружение:
   ```bash
   python -m venv venv
   ```
3. Активируйте виртуальное окружение:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
4. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
5. Скопируйте `.env.example` в `.env` и заполните своими ключами:
   ```
   OW_API_KEY=your_openweather_key
   BOT_TOKEN=your_telegram_token
   ```

## Получение API ключей

### OpenWeather API
1. Зарегистрируйтесь на [openweathermap.org](https://openweathermap.org/api)
2. Получите бесплатный API ключ
3. Добавьте его в `.env` как `OW_API_KEY`

### Telegram Bot Token
1. Найдите [@BotFather](https://t.me/botfather) в Telegram
2. Создайте нового бота командой `/newbot`
3. Скопируйте полученный токен в `.env` как `BOT_TOKEN`

## Использование модулей

### weather_app.py

Модуль предоставляет функции для работы с OpenWeather API:

- `get_coordinates(city: str, limit: int = 1)` - получение координат города
- `get_current_weather(lat: float, lon: float)` - текущая погода
- `get_forecast_5d3h(lat: float, lon: float)` - 5-дневный прогноз с шагом 3 часа
- `get_air_pollution(lat: float, lon: float)` - данные о загрязнении воздуха
- `analyze_air_pollution(components: dict, extended: bool=False)` - анализ загрязнения

### storage.py

Модуль для работы с пользовательскими данными:

- `load_user(user_id: int)` - загрузка данных пользователя
- `save_user(user_id: int, data: dict)` - сохранение данных пользователя

Формат данных в `User_Data.json`:
```json
{
  "123456789": {
    "city": "Москва",
    "lat": 55.7558,
    "lon": 37.6173,
    "notifications": {
      "enabled": true,
      "interval_h": 2
    }
  }
}
```

## Запуск

После настройки всех параметров запустите бота:
```bash
python bot.py
```

## Лицензия

MIT
