import openai
import requests
import logging
import time
from threading import Thread

logging.basicConfig(filename='bot.log', level=logging.INFO)

openai.api_key = 'your-chatgpt-api-key-here'

CLIENT_ID = 'your-avito-client-id'
CLIENT_SECRET = 'your-avito-client-secret'

# Ключевые слова для фильтрации
KEYWORDS_REAL_ESTATE = ["Аренда офиса", "Продажа офиса", "Коммерческая недвижимость"]
KEYWORDS_BUSINESS = ["Маркетинговые услуги", "Реклама для бизнеса"]
KEYWORDS_CONSTRUCTION = ["Строительные услуги", "Строительство домов"]
KEYWORDS_EDUCATION = ["Онлайн-школа", "Образовательные услуги"]

# Переменная для хранения токена
avito_token = None

def get_avito_token():
    """
    Получение токена доступа к API Avito.
    """
    global avito_token
    url = "https://api.avito.ru/token"
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'client_credentials'
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        avito_token = response.json().get('access_token')
        logging.info(f"Новый токен получен: {avito_token}")
    else:
        logging.error(f"Ошибка получения токена: {response.json()}")
        avito_token = None

def auto_refresh_token():
    """
    Автоматическое обновление токена каждые 55 минут.
    """
    while True:
        get_avito_token()
        # Ждем 55 минут перед обновлением токена
        time.sleep(55 * 60)

# Запуск процесса автоматического обновления токена
token_refresh_thread = Thread(target=auto_refresh_token, daemon=True)
token_refresh_thread.start()

def search_avito(keyword):
    """
    Поиск объявлений по ключевым словам.
    """
    if not avito_token:
        logging.error("Токен отсутствует, поиск невозможен.")
        return {}

    url = f'https://www.avito.ru/api/1/items?q={keyword}'
    headers = {
        'Authorization': f'Bearer {avito_token}'
    }
    response = requests.get(url, headers=headers)

    logging.info(f"Поиск по ключевому слову: {keyword} - статус {response.status_code}")

    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Ошибка запроса к API Avito: {response.json()}")
        return {}

def get_chatgpt_response(prompt):
    """
    Генерация ответа с использованием OpenAI ChatGPT.
    """
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=150
        )
        answer = response.choices[0].text.strip()

        logging.info(f"Ответ ChatGPT на запрос '{prompt}': {answer}")
        return answer
    except Exception as e:
        logging.error(f"Ошибка при запросе к ChatGPT: {str(e)}")
        return None
