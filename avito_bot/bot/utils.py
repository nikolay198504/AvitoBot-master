import certifi
import json
import requests
import logging
import time
import openai
import os
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import random
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

# Установка API-ключа OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')  # Рекомендуется использовать переменные окружения

# Avito API Credentials
CLIENT_ID = os.getenv('AVITO_CLIENT_ID')
CLIENT_SECRET = os.getenv('AVITO_CLIENT_SECRET')
SCOPES = 'items:info messenger:read messenger:write seller:read'  # Обновленные scopes

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


def get_random_proxy():
    """
    Возвращает None, чтобы временно отключить использование прокси.
    """
    return None  # Прокси временно отключены


def random_delay(min_delay=2, max_delay=5):
    """
    Вставляет случайную задержку между запросами.

    :param min_delay: Минимальная задержка в секундах.
    :param max_delay: Максимальная задержка в секундах.
    """
    delay = random.uniform(min_delay, max_delay)
    logging.info(f"Задержка между запросами: {delay:.2f} секунд")
    time.sleep(delay)


def get_avito_token(request):
    """
    Получает токен доступа от Avito API с использованием client_credentials.
    """
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
    logging.info(f"Отправляем запрос на получение токена по URL: {url} с данными: {payload}")

    session = get_session_with_retries()

    try:
        # Вставляем случайную задержку перед запросом
        random_delay()

        response = session.post(
            url,
            data=payload,
            headers=headers,
            timeout=60,  # Увеличиваем тайм-аут до 60 секунд
            verify=False
        )
        logging.info(f"Статус-код ответа: {response.status_code}")
        logging.debug(f"Тело ответа: {response.text}")
        response.raise_for_status()
        data = response.json()
        access_token = data.get('access_token')
        if not access_token:
            logging.error("Не удалось получить access_token из ответа")
            request.session['access_token'] = None
            return
        expires_in = data.get('expires_in')  # В секундах (например, 86400 для 24 часов)
        obtained_time = time.time()
        # Сохраняем токен и время получения в сессии
        request.session['access_token'] = access_token
        request.session['token_expires_in'] = expires_in
        request.session['token_obtained_time'] = obtained_time
        logging.info("Успешно получили access_token через client_credentials")
    except requests.exceptions.SSLError as e:
        logging.error(f"SSL ошибка при получении access_token: {str(e)}")
        request.session['access_token'] = None
    except requests.exceptions.Timeout:
        logging.error("Превышено время ожидания при попытке получить access_token")
        request.session['access_token'] = None
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP ошибка при получении access_token: {str(e)} - Ответ: {response.text}")
        request.session['access_token'] = None
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка запроса при получении access_token: {str(e)}")
        request.session['access_token'] = None
    except Exception as e:
        logging.error(f"Непредвиденная ошибка: {str(e)}")
        request.session['access_token'] = None


def is_token_expired(request):
    """
    Проверяет, истёк ли токен доступа.

    :return: True, если токен истёк или отсутствует, иначе False.
    """
    token_obtained_time = request.session.get('token_obtained_time')
    token_expires_in = request.session.get('token_expires_in')
    if token_obtained_time and token_expires_in:
        current_time = time.time()
        # Проверяем, осталось ли меньше 5 минут до истечения токена
        if (token_obtained_time + token_expires_in - TOKEN_REFRESH_BUFFER) <= current_time:
            return True
        else:
            return False
    return True  # Токен отсутствует или данные повреждены


def ensure_valid_token(request):
    """
    Убедиться, что токен доступа действителен. Если нет, получить новый.
    """
    access_token = request.session.get('access_token')
    if is_token_expired(request) or not access_token:
        logging.info("Получение нового access_token...")
        get_avito_token(request)
    else:
        logging.info("Текущий access_token действителен")


def search_avito(request, keyword_list, max_ads=10):
    """
    Ищет объявления на Avito по заданным ключевым словам с использованием Avito API.
    Ограничивает количество найденных объявлений до max_ads.
    """
    logging.info(f"Начат поиск по ключевым словам: {keyword_list}")
    ensure_valid_token(request)

    access_token = request.session.get('access_token')
    if not access_token:
        logging.error("Токен отсутствует, поиск невозможен.")
        return {}

    url = 'https://api.avito.ru/core/v1/items'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    all_ads = []
    per_page = 10  # Устанавливаем количество объявлений на странице
    max_pages = 1  # Ограничиваем до одной страницы для теста

    session = get_session_with_retries()

    for page in range(1, max_pages + 1):
        params = {
            'q': " ".join(keyword_list),
            'per_page': per_page,
            'page': page
        }
        paginated_url = url  # В API URL остаётся тот же

        random_delay()

        try:
            response = session.get(
                paginated_url,
                headers=headers,
                params=params,
                timeout=60,
                verify=False
            )
            logging.info(f"Статус-код ответа: {response.status_code}")
            response.raise_for_status()
            data = response.json()

            if 'resources' not in data:
                logging.error("Некорректный формат ответа от API.")
                break

            ads_on_page = data.get('resources', [])
            all_ads.extend(ads_on_page)

            # Ограничиваем до первых max_ads объявлений
            if len(all_ads) >= max_ads:
                all_ads = all_ads[:max_ads]
                break

        except requests.exceptions.RequestException as e:
            logging.error(f"Ошибка при запросе на странице {page}: {e}")
            break

    logging.info(f"Найдено {len(all_ads)} объявлений.")
    return {'resources': all_ads[:max_ads]}

# Функция для парсинга объявлений с сайта Avito (с ограничением на 10 объявлений)


def send_message_to_client(request, client_id, message):
    """
    Отправляет сообщение клиенту через Avito Messenger API.

    :param request: HTTP запрос Django.
    :param client_id: ID клиента для отправки сообщения.
    :param message: Текст сообщения.
    :return: Ответ API или None.
    """
    ensure_valid_token(request)
    access_token = request.session.get('access_token')

    if not access_token:
        logging.error("Токен отсутствует, отправка сообщения невозможна.")
        return None

    url = f'https://api.avito.ru/messenger/v1/accounts/{client_id}/messages'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    payload = {'text': message}

    session = get_session_with_retries()

    # Вставляем случайную задержку перед запросом
    random_delay()

    try:
        response = session.post(
            url,
            json=payload,
            headers=headers,
            timeout=60,
            verify=certifi.where()
        )
        response.raise_for_status()
        logging.info(f"Сообщение отправлено клиенту с ID {client_id}: {message}")
        return response.json()
    except requests.exceptions.Timeout:
        logging.error(f"Превышено время ожидания при отправке сообщения клиенту с ID {client_id}")
        return None
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP ошибка при отправке сообщения клиенту с ID {client_id}: {str(e)} - Ответ: {response.text}")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка запроса при отправке сообщения клиенту с ID {client_id}: {str(e)}")
        return None


def get_chatgpt_response(ad_description):
    """
    Генерирует рекламное сообщение на основе описания объявления с помощью OpenAI.

    :param ad_description: Описание объявления.
    :return: Сгенерированное сообщение или None.
    """
    prompt = f"Сгенерируй рекламное сообщение на основе этого объявления: {ad_description}. Реклама должна предлагать маркетинговые услуги, которые помогут продать или сдать это имущество быстрее."

    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=150,
            n=1,
            stop=None,
            temperature=0.7,
        )
        answer = response.choices[0].text.strip()
        logging.info(f"Ответ ChatGPT на запрос: {answer}")
        return answer
    except openai.OpenAIError as e:
        logging.error(f"Ошибка при запросе к OpenAI: {str(e)}")
        return None
    except Exception as e:
        logging.error(f"Неизвестная ошибка: {str(e)}")
        return None


def get_seller_info(request, seller_id):
    """
    Получает информацию о продавце по его ID через Avito API.

    :param request: HTTP запрос Django.
    :param seller_id: ID продавца.
    :return: Словарь с информацией о продавце или пустой словарь.
    """
    ensure_valid_token(request)
    access_token = request.session.get('access_token')
    if not access_token:
        logging.error("Токен отсутствует, невозможно получить информацию о продавце.")
        return {}

    url = f'https://api.avito.ru/core/v1/sellers/{seller_id}'  # Проверьте правильность эндпоинта
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    session = get_session_with_retries()

    # Вставляем случайную задержку перед запросом
    random_delay()

    try:
        response = session.get(
            url,
            headers=headers,
            timeout=60,
            verify=certifi.where()
        )
        logging.info(f"Статус-код ответа для продавца {seller_id}: {response.status_code}")
        response.raise_for_status()
        data = response.json()
        logging.info(f"Информация о продавце для ID {seller_id}: {json.dumps(data, ensure_ascii=False, indent=2)}")
        return data
    except requests.exceptions.Timeout:
        logging.error(f"Превышено время ожидания при получении информации о продавце для ID {seller_id}")
        return {}
    except requests.exceptions.HTTPError as http_err:
        logging.error(
            f"HTTP ошибка при получении информации о продавце для ID {seller_id}: {http_err} - Ответ: {response.text}")
        return {}
    except requests.exceptions.RequestException as req_err:
        logging.error(f"Ошибка запроса при получении информации о продавце для ID {seller_id}: {req_err}")
        return {}
    except Exception as e:
        logging.error(f"Непредвиденная ошибка при получении информации о продавце для ID {seller_id}: {str(e)}")
        return {}


def scrape_avito_listings(keyword_list, location='rossiya', category='nedvizhimost', max_pages=5, max_ads=10):
    """
    Парсит объявления на Avito по заданным ключевым словам и возвращает список объявлений.
    По умолчанию ищет по всей России.
    Ограничивает количество найденных объявлений до max_ads.
    """
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

                seller_tag = listing.find('span', {'class': 'seller-info-name'})
                seller = seller_tag.get_text(strip=True) if seller_tag else 'Неизвестен'

                ad = {
                    'title': title,
                    'price': price,
                    'url': url,
                    'seller': seller
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

def get_seller_from_listing(ad_url):
    """
    Парсит страницу объявления для получения информации о продавце.
    """
    session = get_session_with_retries()
    try:
        response = session.get(ad_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=60, verify=certifi.where())
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')

        # Пример поиска блока с информацией о продавце на странице объявления
        seller_info = soup.find('div', {'class': 'seller-info-name'})
        if seller_info:
            seller_name = seller_info.get_text(strip=True)
            return seller_name
        else:
            return "Неизвестен"
    except Exception as e:
        logging.error(f"Ошибка при парсинге страницы объявления: {str(e)}")
        return "Неизвестен"
