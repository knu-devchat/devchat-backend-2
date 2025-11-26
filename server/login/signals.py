from django.dispatch import receiver
from allauth.socialaccount.signals import pre_social_login, social_account_added
from allauth.socialaccount.models import SocialAccount
from .models import User, GithubFriend
import requests

@receiver(pre_social_login)
def populate_user_info(sender, request, sociallogin, **kwargs):
    """GitHub 로그인 시 사용자 정보를 자동으로 채움"""
    if sociallogin.account.provider == 'github':
        user_data = sociallogin.account.extra_data
        user = sociallogin.user
        
        # GitHub 정보를 User 모델에 저장
        user.github_username = user_data.get('login')
        user.github_id = str(user_data.get('id'))
        user.profile_image = user_data.get('avatar_url')
        user.github_bio = user_data.get('bio')
        user.github_company = user_data.get('company')
        user.github_location = user_data.get('location')
        user.github_followers = user_data.get('followers', 0)
        user.github_following = user_data.get('following', 0)
        
        # 이메일이 없으면 GitHub에서 가져오기
        if not user.email:
            user.email = user_data.get('email', '')
        
        user.save()

@receiver(social_account_added)
def fetch_github_friends(sender, request, sociallogin, **kwargs):
    """GitHub 친구 정보를 가져와서 저장"""
    if sociallogin.account.provider == 'github':
        user = sociallogin.user
        social_token = sociallogin.token
        
        if social_token:
            access_token = social_token.token
            
            # GitHub API로 팔로워 정보 가져오기
            try:
                fetch_followers(user, access_token)
                fetch_following(user, access_token)
            except Exception as e:
                print(f"GitHub 친구 정보 가져오기 실패: {e}")

def fetch_followers(user, access_token):
    """팔로워 정보 가져오기"""
    headers = {'Authorization': f'token {access_token}'}
    url = 'https://api.github.com/user/followers'
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        followers = response.json()
        
        for follower in followers:
            GithubFriend.objects.get_or_create(
                user=user,
                friend_github_id=str(follower['id']),
                defaults={
                    'friend_username': follower['login'],
                    'friend_profile_image': follower['avatar_url'],
                    'relationship_type': 'follower'
                }
            )

def fetch_following(user, access_token):
    """팔로잉 정보 가져오기"""
    headers = {'Authorization': f'token {access_token}'}
    url = 'https://api.github.com/user/following'
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        following = response.json()
        
        for follow in following:
            friend, created = GithubFriend.objects.get_or_create(
                user=user,
                friend_github_id=str(follow['id']),
                defaults={
                    'friend_username': follow['login'],
                    'friend_profile_image': follow['avatar_url'],
                    'relationship_type': 'following'
                }
            )
            
            # 이미 팔로워로 존재한다면 mutual로 업데이트
            if not created and friend.relationship_type == 'follower':
                friend.relationship_type = 'mutual'
                friend.save()