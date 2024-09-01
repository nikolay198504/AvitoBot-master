import openai
import requests
import logging

# Настройка логирования
logging.basicConfig(filename='bot.log', level=logging.INFO)

openai.api_key = 'your-chatgpt-api-key-here'

# Ваши ключи API Avito
CLIENT_ID = 'your-avito-client-id'
CLIENT_SECRET = 'your-avito-client-secret'

def get_avito_token():
    url = "https://api.avito.ru/token"
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'client_credentials'
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        return response.json().get('access_token')
    else:
        logging.error(f"Ошибка получения токена: {response.json()}")
        return None

def search_avito(keyword):
    token = get_avito_token()
    if not token:
        logging.error("Не удалось получить токен для доступа к API Avito.")
        return {}

    url = f'https://www.avito.ru/api/1/items?q={keyword}'
    headers = {
        'Authorization': f'Bearer {token}'
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
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=150
    )
    answer = response.choices[0].text.strip()

    # Логирование ответа ChatGPT
    logging.info(f"Ответ ChatGPT на запрос '{prompt}': {answer}")

    return answer


def get_chatgpt_response(prompt):
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=150
    )
    return response.choices[0].text.strip()
