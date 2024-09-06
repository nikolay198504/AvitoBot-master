from django import forms
from .models import Message

# Ключевые слова, которые будут отображены как чекбоксы
KEYWORD_CHOICES = [
    ("Аренда офиса", "Аренда офиса"),
    ("Продажа офиса", "Продажа офиса"),
    ("Коммерческая недвижимость", "Коммерческая недвижимость"),
    ("Маркетинговые услуги", "Маркетинговые услуги"),
    ("Реклама для бизнеса", "Реклама для бизнеса"),
    ("Строительные услуги", "Строительные услуги"),
    ("Строительство домов", "Строительство домов"),
    ("Онлайн-школа", "Онлайн-школа"),
    ("Образовательные услуги", "Образовательные услуги"),
]

class KeywordForm(forms.Form):
    select_all = forms.BooleanField(
        required=False,
        label="Выбрать все",
        widget=forms.CheckboxInput(attrs={'onclick': 'toggleSelectAll()'})
    )
    word = forms.MultipleChoiceField(
        choices=KEYWORD_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        label="Выберите ключевые слова"
    )

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content']
