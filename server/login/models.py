import uuid
from django.contrib.auth.models import User
from django.db import models

# Create your models here.
class UserProfile(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # 기본 필드 확장
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

    def __str__(self):
        return f"{self.user.username}'s profile"

    @property
    def email(self):
        """User 모델의 email에 접근하는 프로퍼티"""
        return self.user.email or ''

    @property
    def username(self):
        """User 모델의 username에 접근하는 프로퍼티"""
        return self.user.username
    
class GithubFriend(models.Model):
    """Github에서 가져온 친구 정보"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='github_friends')
    friend_github_id = models.CharField(max_length=100)
    friend_username = models.CharField(max_length=100)
    friend_profile_image = models.URLField(blank=True, null=True)
    friend_bio = models.TextField(blank=True, null=True)

    # 친구 관계 타입
    RELATIONSHIP_CHOICES = [
        ('follower', 'Follower'),
        ('following', 'Following'),
        ('mutual', 'Mutual'),
    ]

    relationship_type = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES)

    # 해당 친구가 서비스 사용자인지 확인
    service_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='github_connections'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'friend_github_id']

    def __str__(self):
        return f"{self.user.username} -> {self.friend_username} ({self.relationship_type})"