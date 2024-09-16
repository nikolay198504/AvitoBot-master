from django.shortcuts import render
from .forms import MessageForm
from .utils import (
    search_avito,
    scrape_avito_listings,
    # send_message_to_client,  # Закомментируем, чтобы не отправлять сообщения
    get_chatgpt_response,
    ensure_valid_token
)
import logging

# Настройка логирования (если не настроена в utils.py)
logging.basicConfig(
    filename='bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Ключевые слова для отображения в интерфейсе
KEYWORD_CHOICES = [
    ("Аренда офиса", "Аренда офиса"),
    ("Продажа офиса", "Продажа офиса"),
    ("Офис", "Офис"),
    ("Коммерческая недвижимость", "Коммерческая недвижимость"),
    ("Сдача офиса", "Сдача офиса"),
    ("Продажа коммерческой недвижимости", "Продажа коммерческой недвижимости"),
    ("Офисные помещения", "Офисные помещения"),
    ("Коммерческие помещения", "Коммерческие помещения"),
]

def index(request):
    logging.info(f"Запрос получен, метод: {request.method}")

    if request.method == 'GET':
        ensure_valid_token(request)
        message_form = MessageForm()
        return render(request, 'index.html', {
            'message_form': message_form,
            'keywords': KEYWORD_CHOICES
        })

    elif request.method == 'POST':
        message_form = MessageForm(request.POST)
        selected_keywords = request.POST.getlist('keywords')
        parse_method = request.POST.get('parse_method')

        if not selected_keywords:
            logging.error("Ключевые слова не выбраны")
            return render(request, 'index.html', {
                'error': 'Вы должны выбрать хотя бы одно ключевое слово!',
                'message_form': message_form,
                'keywords': KEYWORD_CHOICES
            })

        logging.info(f"Выбраны ключевые слова: {selected_keywords}")

        if message_form.is_valid():
            message = message_form.cleaned_data['content']
        else:
            message = None

        ads = []

        if parse_method == 'api':
            ads_data = search_avito(request, selected_keywords, max_ads=10)
            if ads_data:
                ads = ads_data.get('resources', [])
        elif parse_method == 'scrape':
            ads = scrape_avito_listings(selected_keywords, max_ads=10)

        if ads:
            detailed_ads = []
            for ad in ads:
                detailed_ads.append(ad)

            return render(request, 'results.html', {
                'ads': detailed_ads,
                'keywords': selected_keywords
            })
        else:
            logging.error(f"По ключевым словам {selected_keywords} ничего не найдено")
            return render(request, 'results.html', {
                'ads': [],
                'keywords': selected_keywords,
                'error': 'По вашему запросу ничего не найдено.'
            })


def log_view(request):
    """
    Представление для просмотра логов приложения.
    """
    logs = []
    try:
        with open('bot.log', 'r', encoding='utf-8') as f:
            logs = f.readlines()
    except FileNotFoundError:
        logging.error("Лог-файл не найден.")

    return render(request, 'log_view.html', {'logs': logs})
 