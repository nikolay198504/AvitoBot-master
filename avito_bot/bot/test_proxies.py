# test_proxies.py

import requests
import os
from dotenv import load_dotenv

load_dotenv()

PROXY_LIST = os.getenv('PROXY_LIST')
if not PROXY_LIST:
    print("Список прокси не настроен в .env файле.")
    exit()

proxies = [proxy.strip() for proxy in PROXY_LIST.split(',') if proxy.strip()]

for proxy in proxies:
    proxy_dict = {
        "http": proxy,
        "https": proxy  # Некоторые прокси могут не поддерживать HTTPS
    }
    try:
        # Используем HTTP endpoint для тестирования HTTP-прокси
        response = requests.get('http://httpbin.org/ip', proxies=proxy_dict, timeout=10)
        if response.status_code == 200:
            print(f"Прокси работает: {proxy}")
        else:
            print(f"Прокси не работает: {proxy} - Статус код: {response.status_code}")
    except Exception as e:
        print(f"Прокси не работает: {proxy} - Ошибка: {e}")
