import json
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from .models import AiChatSession 
from chat.models import ChatRoom, Message, UserProfile
from .services import get_ai_response 

User = get_user_model()

class AiChatConsumer(AsyncWebsocketConsumer): 
    async def connect(self):
        # 인증 확인 
        self.user = self.scope.get('user')
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        # URL에서 session_id를 추출하고 유효성 확인
        self.session_id = self.scope["url_route"]["kwargs"].get("session_id")
        
        # AiChatSession 객체 찾기 (DB 접근)
        self.ai_session = await self._get_ai_session(self.session_id)
        if not self.ai_session:
            await self.close()
            return

        self.room_group_name = f"llm_chat_{self.session_id}" 
        
        # 4. 기타 정보 로드
        self.sender_profile = await self._get_user_profile(self.user)
        self.room = self.ai_session.base_room # 채팅방 객체는 AiChatSession에서 가져옴
        self.ai_profile = await self._get_ai_profile() # AI 봇 프로필 로드

        # 5. 그룹 가입 및 연결 수락
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    
    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

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
    
    async def receive(self, text_data=None, bytes_data=None):
        if not text_data: return

        try:
            data = json.loads(text_data)
            message = data.get("message")
        except json.JSONDecodeError:
            return
        
        if not message: return
        
        #사용자의 메시지 저장 및 전파
        stored_message = await self._save_message(self.room, self.sender_profile, message)
        await self._group_send_message(self.sender_profile.username, stored_message)
        
        # AI 호출 
        prompt = message # 사용자의 메시지 전체를 프롬프트로 사용
        await self.process_ai_request(prompt) 


    async def process_ai_request(self, prompt: str):
        """LLM 서비스 호출 및 응답을 채팅방에 전파합니다."""
        
        # AI 서비스 호출
        ai_text = await get_ai_response(prompt)

        # AI 응답을 DB에 저장
        stored_response = await self._save_message(self.room, self.ai_profile, ai_text)
        
        # AI 응답을 그룹 전송
        await self._group_send_message(self.ai_profile.username, stored_response)


    @database_sync_to_async
    def _get_ai_session(self, session_id):
        """session_id로 AiChatSession 객체를 가져옵니다."""
        try:
            return AiChatSession.objects.get(session_id=session_id)
        except AiChatSession.DoesNotExist:
            return None
    
    @database_sync_to_async
    def _get_user_profile(self, user) -> UserProfile:
        return UserProfile.objects.get(user=user) 
    
    @database_sync_to_async
    def _get_ai_profile(self):
        """AI 봇을 위한 UserProfile 객체를 가져옵니다. (없으면 생성)"""
        # AI 봇의 username을 'GeminiBot' 등으로 가정하고, UserProfile을 찾거나 생성합니다.
        # 실제 구현에서는 Django User 모델이 필요할 수 있습니다.
        # 여기서는 테스트를 위해 pk=1인 사용자를 AI 프로필로 임시 가정합니다.
        return UserProfile.objects.get(pk=1) 
        
    @database_sync_to_async
    def _save_message(self, room: ChatRoom, sender: UserProfile, content: str) -> Message:
        return Message.objects.create(chatroom=room, sender=sender, content=content)

    async def _group_send_message(self, username, message_obj):
        """메시지를 그룹에 전파하는 헬퍼 함수"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message_obj.content,
                "username": username,
                "message_id": message_obj.id,
                "created_at": message_obj.created_at.isoformat(),
            },
        )