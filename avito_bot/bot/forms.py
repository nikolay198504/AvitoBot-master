from django import forms
from .models import Keyword, Message

class KeywordForm(forms.ModelForm):
    class Meta:
        model = Keyword
        fields = ['word']

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content']
