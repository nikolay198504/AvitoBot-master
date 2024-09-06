from django.shortcuts import render, redirect
from .models import Keyword, Message, LogEntry, AvitoAd
from .forms import KeywordForm, Message
from .utils import search_avito, get_chatgpt_response
import logging

# Настройка логирования
logging.basicConfig(filename='bot.log', level=logging.INFO)

def index(request):
    if request.method == 'POST':
        keyword_form = KeywordForm(request.POST)
        message_form = Message(request.POST)

        if keyword_form.is_valid() and message_form.is_valid():
            selected_keywords = keyword_form.cleaned_data['word']
            message = message_form.save()

            for keyword in selected_keywords:
                ads = search_avito(keyword)
                if ads and 'result' in ads and 'ads' in ads['result']:
                    for ad in ads['result']['ads']:
                        AvitoAd.objects.create(
                            keyword=keyword,  # Используем связанный объект Keyword
                            title=ad.get('title', 'Нет заголовка'),
                            description=ad.get('description', ''),
                            url=ad.get('url', ''),
                            price=ad.get('price', 0)
                        )
                        response = get_chatgpt_response(ad['description'])
                        # Логирование результата работы
                        LogEntry.objects.create(
                            keyword=keyword,
                            message=message,
                            response=response
                        )
                else:
                    # Логирование ошибки, если результат не соответствует ожиданиям
                    logging.error(f"Некорректный ответ от API Avito: {ads}")

            return redirect('log_view')
    else:
        keyword_form = KeywordForm()
        message_form = Message()

    return render(request, 'index.html', {'keyword_form': keyword_form, 'message_form': message_form})

def log_view(request):
    logs = LogEntry.objects.all()
    return render(request, 'log_view.html', {'logs': logs})
