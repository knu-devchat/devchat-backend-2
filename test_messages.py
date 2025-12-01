from chat.models import Message

msgs = Message.objects.all()[:10]
print(f'\n총 메시지 수: {Message.objects.count()}\n')
print('=' * 80)

for m in msgs:
    room_name = m.room.name if m.room else "None"
    content_preview = m.content[:50] if len(m.content) > 50 else m.content
    print(f'ID: {m.id}')
    print(f'방: {room_name}')
    print(f'AI 채팅: {m.is_ai_chat}')
    print(f'내용: {content_preview}')
    print(f'작성자: {m.user.username}')
    print('-' * 80)
