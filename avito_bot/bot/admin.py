from django.contrib import admin
from .models import Keyword, Message, LogEntry, AvitoAd

@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    list_display = ('word', 'created_at')
    search_fields = ('word',)

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('content', 'created_at')
    search_fields = ('content',)

@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('keyword', 'message', 'response', 'created_at')
    search_fields = ('keyword__word', 'message__content', 'response')
    list_filter = ('created_at',)

@admin.register(AvitoAd)
class AvitoAdAdmin(admin.ModelAdmin):
    list_display = ('title', 'keyword', 'price', 'created_at')
    search_fields = ('title', 'description', 'keyword__word')
    list_filter = ('created_at', 'price')
