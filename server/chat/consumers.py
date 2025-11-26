import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import ChatRoom, Message


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"].get("room_name")
        self.room_group_name = f"chat_{self.room_name}"
        self.room = await self._get_or_create_room(self.room_name)

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        message = data.get("message")
        username = data.get("username", "")
        if not message:
            return

        stored_message = await self._save_message(self.room, username, message)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message,
                "username": username,
                "message_id": stored_message.id,
                "created_at": stored_message.created_at.isoformat(),
            },
        )

    async def chat_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "message": event.get("message"),
                    "username": event.get("username", ""),
                    "message_id": event.get("message_id"),
                    "created_at": event.get("created_at"),
                }
            )
        )

    @database_sync_to_async
    def _get_or_create_room(self, room_name: str) -> ChatRoom:
        room, _ = ChatRoom.objects.get_or_create(room_name=room_name)
        return room

    @database_sync_to_async
    def _save_message(self, room: ChatRoom, username: str, content: str) -> Message:
        return Message.objects.create(room=room, username=username, content=content)