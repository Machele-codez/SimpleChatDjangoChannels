from django.db import models

# Create your models here.
class ChatMessage(models.Model):
    username = models.CharField(max_length=255)
    room_name = models.CharField(max_length=255)
    message_text = models.TextField()
    date_time_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('date_time_added',)