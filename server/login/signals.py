# login/signals.py
from django.dispatch import receiver
from django.contrib.auth.models import User
from allauth.socialaccount.signals import pre_social_login, social_account_added
from allauth.socialaccount.models import SocialAccount, SocialToken
from .models import UserProfile, GithubFriend
import requests
from django.db.models.signals import post_save

@receiver(pre_social_login)
def handle_pre_social_login(sender, request, sociallogin, **kwargs):
    """GitHub 로그인 전 처리 - username 중복 해결"""
    if sociallogin.account.provider == 'github':
        user_data = sociallogin.account.extra_data
        github_id = str(user_data.get('id'))
        github_username = user_data.get('login')

        # 기존에 같은 Github ID로 연결된 UserProfile 찾기
        try:
            existing_profile = UserProfile.objects.get(github_id=github_id)
            existing_user = existing_profile.user

            # 기존 사용자로 로그인 처리
            sociallogin.user = existing_user
            return
        
        except UserProfile.DoesNotExist:
            print(f"[DEBUG] 새로운 Github 계정")
        
        # 새로운 계정인 경우 username 중복 체크
        if github_username:
            original_username = github_username
            username = github_username
            counter = 1
            
            while User.objects.filter(username=username).exists():
                username = f"{original_username}_{counter}"
                counter += 1

            sociallogin.user.username = username
        
        # 이메일 설정
        if not sociallogin.user.email:
            email = user_data.get('email')
            if email:
                sociallogin.user.email = email
            else:
                temp_email = f"{username}@github.temp"
                sociallogin.user.email = temp_email
        
        # User 모델의 기본 필드만 설정
        name = user_data.get('name', '')
        if name:
            name_parts = name.split(' ', 1)
            sociallogin.user.first_name = name_parts[0]
            if len(name_parts) > 1:
                sociallogin.user.last_name = name_parts[1]

@receiver(social_account_added)
def handle_social_account_added(sender, request, sociallogin, **kwargs):
    """소셜 계정 추가 후 UserProfile에 GitHub 정보 저장"""
    if sociallogin.account.provider == 'github':
        user = sociallogin.user
        user_data = sociallogin.account.extra_data
        
        # UserProfile에만 GitHub 정보 저장 (User 모델이 아님!)
        try:
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'github_username': user_data.get('login', ''),
                    'github_id': str(user_data.get('id', '')),
                    'profile_image': user_data.get('avatar_url', ''),
                    'github_bio': user_data.get('bio', ''),
                    'github_company': user_data.get('company', ''),
                    'github_location': user_data.get('location', ''),
                    'github_followers': user_data.get('followers', 0),
                    'github_following': user_data.get('following', 0),
                }
            )
            
            # 이미 존재하는 프로필이라면 업데이트
            if not created:
                profile.github_username = user_data.get('login', '')
                profile.github_id = str(user_data.get('id', ''))
                profile.profile_image = user_data.get('avatar_url', '')
                profile.github_bio = user_data.get('bio', '')
                profile.github_company = user_data.get('company', '')
                profile.github_location = user_data.get('location', '')
                profile.github_followers = user_data.get('followers', 0)
                profile.github_following = user_data.get('following', 0)
                profile.save()
        
        except Exception as e:
            print(f"[ERROR] Failed to create/update UserProfile: {e}")
        
        # GitHub 친구 정보 가져오기 (안전하게 처리)
        try:
            fetch_github_friends_async(user, sociallogin.account)
        except Exception as e:
            print(f"[ERROR] GitHub 친구 정보 가져오기 실패: {e}")

def fetch_github_friends_async(user, social_account):
    """GitHub 친구 정보를 가져와서 저장"""
    try:
        # SocialToken을 올바르게 가져오기
        social_token = SocialToken.objects.filter(
            account=social_account,
            account__provider='github'
        ).first()
        
        if not social_token:
            return
            
        access_token = social_token.token
        
        # GitHub API 호출
        fetch_followers(user, access_token)
        fetch_following(user, access_token)
        
    except Exception as e:
        print(f"[ERROR] GitHub 친구 정보 가져오기 중 오류: {e}")

def fetch_followers(user, access_token):
    """팔로워 정보 가져오기"""
    try:
        headers = {
            'Authorization': f'token {access_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        url = 'https://api.github.com/user/followers'
        
        response = requests.get(url, headers=headers, timeout=10)
        
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
        else:
            print(f"[ERROR] 팔로워 정보 가져오기 실패: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"[ERROR] 팔로워 정보 처리 중 오류: {e}")

def fetch_following(user, access_token):
    """팔로잉 정보 가져오기"""
    try:
        headers = {
            'Authorization': f'token {access_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        url = 'https://api.github.com/user/following'
        
        response = requests.get(url, headers=headers, timeout=10)
        
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
        else:
            print(f"[ERROR] 팔로잉 정보 가져오기 실패: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"[ERROR] 팔로잉 정보 처리 중 오류: {e}")

@receiver(post_save, sender=User)
def handle_user_post_save(sender, instance, created, **kwargs):
    """User 생성 후 UserProfile에 GitHub 정보 추가"""
    if created:
        # GitHub Social Account가 있는지 확인
        try:
            from allauth.socialaccount.models import SocialAccount
            social_account = SocialAccount.objects.filter(
                user=instance, 
                provider='github'
            ).first()
            
            if social_account:
                print(f"[DEBUG] Found GitHub social account")
                user_data = social_account.extra_data
                
                # UserProfile 업데이트
                try:
                    profile = UserProfile.objects.get(user=instance)
                    profile.github_username = user_data.get('login', '')
                    profile.github_id = str(user_data.get('id', ''))
                    profile.profile_image = user_data.get('avatar_url', '')
                    profile.github_bio = user_data.get('bio', '')
                    profile.github_company = user_data.get('company', '')
                    profile.github_location = user_data.get('location', '')
                    profile.github_followers = user_data.get('followers', 0)
                    profile.github_following = user_data.get('following', 0)
                    profile.save()
                except UserProfile.DoesNotExist:
                    print(f"[DEBUG] UserProfile not found for {instance.username}")
            else:
                print(f"[DEBUG] No GitHub social account found")
                
        except Exception as e:
            print(f"[ERROR] post_save handler: {e}")