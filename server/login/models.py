from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.
class User(AbstractUser):
    # 기본 필드 확장
    email = models.EmailField(unique=True)
    profile_image = models.URLField(blank=True, null=True)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Github 관련 필드
    github_username = models.CharField(max_length=100, blank=True, null=True)
    github_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    github_access_token = models.TextField(blank=True, null=True)
    github_bio = models.TextField(blank=True, null=True)
    github_company = models.CharField(max_length=200, blank=True, null=True)
    github_location = models.CharField(max_length=200, blank=True, null=True)
    github_followers = models.IntegerField(default=0)
    github_following = models.IntegerField(default=0)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email or self.username
    
