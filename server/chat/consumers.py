import json
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from .models import ChatRoom, Message, UserProfile

# Django User 모델 가져오기
User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # 1. 인증 확인 (AuthMiddlewareStack을 통해 scope에 추가된 user 객체 사용)
        self.user = self.scope.get('user')

        if not self.user or not self.user.is_authenticated:
            # 인증되지 않은 사용자라면 연결을 거부합니다.
            await self.close()
            return

        self.room_name = self.scope["url_route"]["kwargs"].get("room_name")
        self.room_group_name = f"chat_{self.room_name}"
        
        # UserProfile 가져오기 (메시지 저장 시 sender로 사용)
        self.sender_profile = await self._get_user_profile(self.user)
        # username을 미리 저장 (async context에서 DB 접근 방지)
        self.username = self.user.username
        
        # 채팅방 존재 여부 확인
        self.room = await self._get_room(self.room_name)
        if not self.room:
            # 채팅방이 없으면 연결 종료
            await self.close()
            return

        # 그룹 가입 및 연결 수락
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        message = data.get("message")
        if not message:
            return

        # 2. 메시지 저장: UserProfile 객체를 sender로 전달
        stored_message = await self._save_message(self.room, self.sender_profile, message)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message,
                "username": self.username, # 미리 저장된 username 사용
                "message_id": stored_message.id,
                "created_at": stored_message.created_at.isoformat(),
            },
        )

    async def chat_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "message": event.get("message"),
                    "username": event.get("username", "Unknown"),
                    "message_id": event.get("message_id"),
                    "created_at": event.get("created_at"),
                }
            )
        )

    @database_sync_to_async
    def _get_user_profile(self, user) -> UserProfile:
        """Django User 객체를 통해 연결된 UserProfile을 가져옵니다."""
        # Django User와 UserProfile의 관계를 사용 (user=user)
        # UserProfile이 없으면 자동으로 생성
        profile, created = UserProfile.objects.get_or_create(user=user)
        return profile 

    @database_sync_to_async
    def _get_room(self, room_name: str) -> ChatRoom:
        """채팅방 이름을 통해 ChatRoom 객체를 가져옵니다."""
        try:
            return ChatRoom.objects.get(room_name=room_name)
        except ChatRoom.DoesNotExist:
            return None

    @database_sync_to_async
    def _save_message(self, room: ChatRoom, sender: UserProfile, content: str) -> Message:
        """메시지를 DB에 저장합니다."""
        # Message 모델의 필드(room, sender, content)에 맞게 저장
        return Message.objects.create(room=room, sender=sender, content=content)