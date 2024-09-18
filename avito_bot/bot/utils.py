import os
import certifi
import json
import requests
import logging
import time
import random
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import urllib3  # Импортируем urllib3 для отключения предупреждений

# Отключаем предупреждения о небезопасных SSL-соединениях
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Загрузка переменных окружения из файла .env
load_dotenv()

# Настройка логирования
logging.basicConfig(
    filename='bot.log',
    level=logging.DEBUG,  # Уровень DEBUG для детального логирования
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    encoding='utf-8'
)

# Avito API Credentials
CLIENT_ID = os.getenv('AVITO_CLIENT_ID')
CLIENT_SECRET = os.getenv('AVITO_CLIENT_SECRET')
SCOPES = 'items:info messenger:read messenger:write seller:read'

# Константа для обновления токена за 5 минут до истечения срока действия
TOKEN_REFRESH_BUFFER = 5 * 60  # 5 минут в секундах


def get_session_with_retries():
    """Создаёт сессию с механизмом повторных попыток."""
    session = requests.Session()
    retries = Retry(
        total=3,  # Общее количество попыток
        backoff_factor=2,  # Интервал между попытками: 2, 4, 8 секунд
        status_forcelist=[500, 502, 503, 504],  # Коды ошибок, при которых выполняется повторная попытка
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    return session


def random_delay(min_delay=2, max_delay=5):
    """Вставляет случайную задержку между запросами."""
    delay = random.uniform(min_delay, max_delay)
    logging.info(f"Задержка между запросами: {delay:.2f} секунд")
    time.sleep(delay)


def get_avito_token(request):
    """Получает токен доступа от Avito API с использованием client_credentials."""
    logging.info("Начало выполнения функции get_avito_token")
    url = 'https://api.avito.ru/token'
    payload = {
        'grant_type': 'client_credentials',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'scope': SCOPES
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    session = get_session_with_retries()

    try:
        random_delay()

        response = session.post(
            url,
            data=payload,
            headers=headers,
            timeout=120,
            verify=False
        )
        logging.info(f"Статус-код ответа: {response.status_code}")
        response.raise_for_status()
        data = response.json()
        access_token = data.get('access_token')
        if not access_token:
            logging.error("Не удалось получить access_token из ответа")
            request.session['access_token'] = None
            return
        expires_in = data.get('expires_in')  # В секундах (например, 86400 для 24 часов)
        obtained_time = time.time()
        request.session['access_token'] = access_token
        request.session['token_expires_in'] = expires_in
        request.session['token_obtained_time'] = obtained_time
        logging.info("Успешно получили access_token через client_credentials")
    except Exception as e:
        logging.error(f"Ошибка при получении access_token: {str(e)}")
        request.session['access_token'] = None


def is_token_expired(request):
    """Проверяет, истёк ли токен доступа."""
    token_obtained_time = request.session.get('token_obtained_time')
    token_expires_in = request.session.get('token_expires_in')
    if token_obtained_time and token_expires_in:
        current_time = time.time()
        if (token_obtained_time + token_expires_in - TOKEN_REFRESH_BUFFER) <= current_time:
            return True
        else:
            return False
    return True


def ensure_valid_token(request):
    """Убедиться, что токен доступа действителен. Если нет, получить новый."""
    access_token = request.session.get('access_token')
    if is_token_expired(request) or not access_token:
        logging.info("Получение нового access_token...")
        get_avito_token(request)
    else:
        logging.info("Текущий access_token действителен")


def scrape_avito_listings(keyword_list, location='rossiya', category='nedvizhimost', max_pages=5, max_ads=10):
    """Парсит объявления на Avito по заданным ключевым словам и возвращает список объявлений."""
    base_url = 'https://www.avito.ru'
    search_url = f"{base_url}/{location}/{category}?q={'+'.join(keyword_list)}"
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }

    session = get_session_with_retries()
    all_ads = []

    for page in range(1, max_pages + 1):
        paginated_url = f"{search_url}&p={page}"
        logging.info(f"Парсинг страницы {page}: {paginated_url}")

        random_delay()

        try:
            response = session.get(paginated_url, headers=headers, timeout=60, verify=certifi.where())
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'lxml')
            listings = soup.find_all('div', {'data-marker': 'item'})

            for listing in listings:
                title_tag = listing.find('h3')
                title = title_tag.get_text(strip=True) if title_tag else 'Без названия'

                price_tag = listing.find('span', {'itemprop': 'price'})
                price = price_tag.get_text(strip=True) if price_tag else 'Не указано'

                url_tag = listing.find('a', {'itemprop': 'url'})
                url = base_url + url_tag['href'] if url_tag else '#'

                ad = {
                    'title': title,
                    'price': price,
                    'url': url,
                }
                all_ads.append(ad)

                if len(all_ads) >= max_ads:
                    logging.info("Достигнуто максимальное количество объявлений")
                    return all_ads

            pagination = soup.find('div', {'data-marker': 'pagination'})
            if not pagination or f"?p={page + 1}" not in pagination.get_text():
                logging.info("Больше страниц нет.")
                break

        except requests.exceptions.RequestException as e:
            logging.error(f"Ошибка при парсинге страницы {page}: {e}")
            break

    logging.info(f"Всего найдено объявлений: {len(all_ads)}")
    return all_ads[:max_ads]
