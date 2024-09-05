import openai
import requests
import logging
import time
from threading import Thread

# Настройка логирования
logging.basicConfig(filename='bot.log', level=logging.INFO)

openai.api_key = 'your-chatgpt-api-key-here'

# Ваши ключи API Avito
CLIENT_ID = 'your-avito-client-id'
CLIENT_SECRET = 'your-avito-client-secret'

# Глобальные переменные для хранения токена и времени его получения
avito_token = None
token_last_updated = None

def get_avito_token():
    global avito_token, token_last_updated

    url = "https://api.avito.ru/token"
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'client_credentials'
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        avito_token = response.json().get('access_token')
        token_last_updated = time.time()
        logging.info(f"Новый токен получен: {avito_token}")
    else:
        logging.error(f"Ошибка получения токена: {response.json()}")
        avito_token = None

def auto_refresh_token():
    while True:
        get_avito_token()
        # Ждем 55 минут перед обновлением токена
        time.sleep(55 * 60)

# Запуск процесса автоматического обновления токена
token_refresh_thread = Thread(target=auto_refresh_token, daemon=True)
token_refresh_thread.start()

def search_avito(keyword):
    global avito_token

    if not avito_token:
        logging.error("Токен отсутствует, поиск невозможен.")
        return {}

    url = f'https://www.avito.ru/api/1/items?q={keyword}'
    headers = {
        'Authorization': f'Bearer {avito_token}'
    }
    response = requests.get(url, headers=headers)

    # Логирование поиска
    logging.info(f"Поиск по ключевому слову: {keyword} - статус {response.status_code}")

    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Ошибка запроса к API Avito: {response.json()}")
        return {}

def get_chatgpt_response(prompt):
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=150
        )
        answer = response.choices[0].text.strip()

        # Логирование ответа ChatGPT
        logging.info(f"Ответ ChatGPT на запрос '{prompt}': {answer}")

        return answer
    except Exception as e:
        logging.error(f"Ошибка при получении ответа от ChatGPT: {str(e)}")
        return "Произошла ошибка при получении ответа от ChatGPT."

# Пример вызова поиска
if __name__ == "__main__":
    # Подождем немного, чтобы токен успел обновиться
    time.sleep(5)
    result = search_avito("iphone")
    print(result)
