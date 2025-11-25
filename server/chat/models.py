from django.db import models

# Create your models here.
class ChatRoom(models.Model):
    room_id = models.AutoField(primary_key=True)
    room_name = models.CharField(max_length=50, unique=True)

class SecureData(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)
    encrypted_value = models.TextField()  # base64 암호문 저장
    created_at = models.DateTimeField(auto_now_add=True)


class Message(models.Model):
    room = models.ForeignKey(
        ChatRoom, on_delete=models.CASCADE, related_name="messages"
    )
    username = models.CharField(max_length=150, blank=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.username or 'Anonymous'}: {self.content[:20]}"