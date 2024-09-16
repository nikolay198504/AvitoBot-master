from django.db import models

class Keyword(models.Model):
    word = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.word


class Message(models.Model):
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.content


class AvitoAd(models.Model):
    keyword = models.ForeignKey(Keyword, on_delete=models.CASCADE, related_name='ads')
    title = models.CharField(max_length=255)
    description = models.TextField()
    url = models.URLField()
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class LogEntry(models.Model):
    keyword = models.ForeignKey(Keyword, on_delete=models.CASCADE)
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"LogEntry for {self.keyword.word} on {self.created_at}"
