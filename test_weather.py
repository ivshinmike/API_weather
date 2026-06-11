"""
Тестовый скрипт для проверки функций weather_app.py
"""
import weather_app

def test_get_coordinates():
    """Тест функции get_coordinates"""
    print("=" * 50)
    print("Тест: get_coordinates")
    print("=" * 50)
    
    # Тест 1: Валидный город
    print("\n1. Тест с валидным городом (Москва):")
    coords = weather_app.get_coordinates("Москва")
    result_coords = coords  # Сохраняем результат для возврата
    if coords:
        print(f"   [OK] Успешно: lat={coords[0]}, lon={coords[1]}")
    else:
        print("   [ERROR] Ошибка: не удалось получить координаты")
    
    # Тест 2: Невалидный город
    print("\n2. Тест с невалидным городом (НесуществующийГород123):")
    coords = weather_app.get_coordinates("НесуществующийГород123")
    if coords is None:
        print("   [OK] Успешно: вернул None для несуществующего города")
    else:
        print(f"   [ERROR] Ошибка: вернул {coords} вместо None")
    
    # Тест 3: Пустая строка
    print("\n3. Тест с пустой строкой:")
    coords = weather_app.get_coordinates("")
    if coords is None:
        print("   [OK] Успешно: вернул None для пустой строки")
    else:
        print(f"   [ERROR] Ошибка: вернул {coords} вместо None")
    
    return result_coords if result_coords else None


def test_get_current_weather(lat, lon):
    """Тест функции get_current_weather"""
    print("\n" + "=" * 50)
    print("Тест: get_current_weather")
    print("=" * 50)
    
    if not lat or not lon:
        print("   [!] Пропущено: нет координат для теста")
        return {}
    
    print(f"\nТест с координатами: lat={lat}, lon={lon}")
    weather = weather_app.get_current_weather(lat, lon)
    
    if weather:
        print("   [OK] Успешно: получены данные о погоде")
        if "name" in weather:
            print(f"   Город: {weather.get('name', 'N/A')}")
        if "main" in weather:
            temp = weather["main"].get("temp", "N/A")
            print(f"   Температура: {temp}°C")
        if "weather" in weather and len(weather["weather"]) > 0:
            desc = weather["weather"][0].get("description", "N/A")
            print(f"   Описание: {desc}")
    else:
        print("   [ERROR] Ошибка: не удалось получить данные о погоде")
    
    return weather


def test_get_forecast_5d3h(lat, lon):
    """Тест функции get_forecast_5d3h"""
    print("\n" + "=" * 50)
    print("Тест: get_forecast_5d3h")
    print("=" * 50)
    
    if not lat or not lon:
        print("   [!] Пропущено: нет координат для теста")
        return []
    
    print(f"\nТест с координатами: lat={lat}, lon={lon}")
    forecast = weather_app.get_forecast_5d3h(lat, lon)
    
    if forecast:
        print(f"   [OK] Успешно: получено {len(forecast)} записей прогноза")
        if len(forecast) > 0:
            first = forecast[0]
            if "dt_txt" in first:
                print(f"   Первая запись: {first['dt_txt']}")
            if "main" in first:
                temp = first["main"].get("temp", "N/A")
                print(f"   Температура: {temp}°C")
    else:
        print("   [ERROR] Ошибка: не удалось получить прогноз")
    
    return forecast


def test_get_air_pollution(lat, lon):
    """Тест функции get_air_pollution"""
    print("\n" + "=" * 50)
    print("Тест: get_air_pollution")
    print("=" * 50)
    
    if not lat or not lon:
        print("   [!] Пропущено: нет координат для теста")
        return {}
    
    print(f"\nТест с координатами: lat={lat}, lon={lon}")
    pollution = weather_app.get_air_pollution(lat, lon)
    
    if pollution:
        print("   [OK] Успешно: получены данные о загрязнении")
        print("   Компоненты:")
        for key, value in pollution.items():
            print(f"     {key}: {value}")
    else:
        print("   [ERROR] Ошибка: не удалось получить данные о загрязнении")
    
    return pollution


def test_analyze_air_pollution(components):
    """Тест функции analyze_air_pollution"""
    print("\n" + "=" * 50)
    print("Тест: analyze_air_pollution")
    print("=" * 50)
    
    if not components:
        print("   [!] Пропущено: нет данных о загрязнении для теста")
        return {}
    
    print("\n1. Тест с extended=False:")
    analysis = weather_app.analyze_air_pollution(components, extended=False)
    if analysis:
        print(f"   [OK] Статус: {analysis.get('status', 'N/A')} (Индекс: {analysis.get('index', 'N/A')})")
        print(f"   Сообщение: {analysis.get('message', 'N/A')}")
    
    print("\n2. Тест с extended=True:")
    analysis_extended = weather_app.analyze_air_pollution(components, extended=True)
    if analysis_extended:
        print(f"   [OK] Общий статус: {analysis_extended.get('status_ru', 'N/A')} (Индекс: {analysis_extended.get('index', 'N/A')})")
        print(f"   Сообщение: {analysis_extended.get('message', 'N/A')}")
        
        if "above_norm" in analysis_extended:
            above = analysis_extended["above_norm"]
            if above:
                print(f"\n   Превышают норму ({len(above)}):")
                for item in above:
                    print(f"     - {item.get('pollutant', 'N/A')}: {item.get('value', 'N/A')} мкг/м3 "
                          f"(норма: {item.get('norm', 'N/A')}, превышение: {item.get('excess', 'N/A')}, "
                          f"статус: {item.get('status', 'N/A')})")
            else:
                print("\n   [OK] Все показатели в норме")
        
        if "below_norm" in analysis_extended:
            below = analysis_extended["below_norm"]
            if below:
                print(f"\n   В пределах нормы ({len(below)}):")
                for item in below:
                    print(f"     - {item.get('pollutant', 'N/A')}: {item.get('value', 'N/A')} мкг/м3 "
                          f"(норма: {item.get('norm', 'N/A')}, статус: {item.get('status', 'N/A')})")
        
        if "summary" in analysis_extended:
            summary = analysis_extended["summary"]
            print(f"\n   Сводка:")
            print(f"     Всего загрязнителей: {summary.get('total_pollutants', 'N/A')}")
            print(f"     Превышают норму: {summary.get('above_norm_count', 'N/A')}")
            print(f"     В пределах нормы: {summary.get('below_norm_count', 'N/A')}")
            if summary.get('worst_pollutant'):
                worst = summary['worst_pollutant']
                print(f"     Худший показатель: {worst.get('pollutant', 'N/A')} "
                      f"(индекс: {worst.get('index', 'N/A')})")
    
    # Тест с пустым словарем
    print("\n3. Тест с пустым словарем:")
    empty_analysis = weather_app.analyze_air_pollution({}, extended=False)
    if empty_analysis:
        print(f"   [OK] Статус: {empty_analysis.get('status', 'N/A')}")
        print(f"   Сообщение: {empty_analysis.get('message', 'N/A')}")
    
    return analysis_extended


def main():
    """Основная функция для запуска всех тестов"""
    print("\n" + "=" * 50)
    print("ТЕСТИРОВАНИЕ МОДУЛЯ weather_app.py")
    print("=" * 50)
    
    # Проверка наличия API ключа
    if not weather_app.OW_API_KEY:
        print("\n[!] ВНИМАНИЕ: OW_API_KEY не установлен в .env файле!")
        print("   Некоторые тесты могут не работать.")
    else:
        print(f"\n[OK] API ключ найден: {weather_app.OW_API_KEY[:10]}...")
    
    # Запуск тестов
    coords = test_get_coordinates()
    
    if coords:
        lat, lon = coords
        weather = test_get_current_weather(lat, lon)
        forecast = test_get_forecast_5d3h(lat, lon)
        pollution = test_get_air_pollution(lat, lon)
        analysis = test_analyze_air_pollution(pollution)
    else:
        print("\n[!] Не удалось получить координаты. Продолжаем с тестовыми координатами Москвы...")
        lat, lon = 55.7558, 37.6173
        weather = test_get_current_weather(lat, lon)
        forecast = test_get_forecast_5d3h(lat, lon)
        pollution = test_get_air_pollution(lat, lon)
        analysis = test_analyze_air_pollution(pollution)
    
    print("\n" + "=" * 50)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 50)
    print("\nРезультаты:")
    print(f"  - get_coordinates: {'[OK]' if coords else '[ERROR]'}")
    print(f"  - get_current_weather: {'[OK]' if weather else '[ERROR]'}")
    print(f"  - get_forecast_5d3h: {'[OK]' if forecast else '[ERROR]'}")
    print(f"  - get_air_pollution: {'[OK]' if pollution else '[ERROR]'}")
    print(f"  - analyze_air_pollution: {'[OK]' if analysis else '[ERROR]'}")


if __name__ == "__main__":
    main()
