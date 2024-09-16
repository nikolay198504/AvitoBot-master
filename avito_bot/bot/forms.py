# forms.py

from django import forms


class MessageForm(forms.Form):
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'cols': 40,
            'class': 'form-control',
            'placeholder': 'Введите сообщение, которое будет отправлено клиентам...'
        }),
        required=False,
        label='Сообщение (не обязательно):'
    )

    PARSE_METHOD_CHOICES = [
        ('api', 'Использовать API'),
        ('scrape', 'Использовать Scraping'),
    ]

    parse_method = forms.ChoiceField(
        choices=PARSE_METHOD_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        required=True,
        label='Метод получения данных:'
    )
