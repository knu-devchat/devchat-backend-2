# LLM AI Chat 구현 완료

## 📋 개요
메인 브랜치의 코드 스타일을 참고하여 LLM AI 채팅 기능을 완전히 재작성했습니다.

## 🎯 주요 개선 사항

### 1. **상세한 디버그 로깅**
- 모든 주요 동작에 `[AI_DEBUG]`, `[AI_ERROR]`, `[AI_SUCCESS]` 로그 추가
- 메인 브랜치와 동일한 로깅 스타일 적용
- 문제 발생 시 디버깅 용이

### 2. **안전한 에러 처리**
- 모든 데이터베이스 접근에 try-except 적용
- `get_or_create` 패턴 사용으로 안전성 향상
- AI 프로필 하드코딩 제거 (pk=1 → AI_Assistant 자동 생성)
- 채팅방 ID 하드코딩 제거 (room_uuid 기반 조회)

### 3. **권한 확인 시스템**
- AI 세션 접근 시 채팅방 권한 검증
- 방장이거나 참가자만 AI 세션 생성 가능
- views.py에서도 동일한 권한 검증 로직 적용

### 4. **메시지 타입 시스템**
메인 브랜치와 동일한 메시지 타입 구조:
- `chat_message`: 일반 채팅 메시지 (사용자 & AI)
- `ai_joined`: AI 참여 알림
- `ai_thinking`: AI 응답 생성 중 표시
- `ai_error`: AI 에러 메시지

### 5. **프론트엔드 호환성**
- `is_self`: 본인 메시지 여부
- `is_ai`: AI 메시지 여부
- `timestamp`: ISO 형식 시간
- `message_id`: 메시지 고유 ID

## 📁 생성된 파일

```
server/llm/
├── __init__.py          # 앱 초기화
├── apps.py              # 앱 설정
├── admin.py             # Django 관리자 설정
├── models.py            # AiChatSession 모델
├── views.py             # REST API 엔드포인트
├── urls.py              # URL 라우팅
├── routing.py           # WebSocket 라우팅
├── consumers.py         # AI WebSocket Consumer
├── services.py          # OpenAI API 서비스
└── migrations/
    └── __init__.py
```

## 🔌 API 엔드포인트

### 1. AI 세션 생성
```http
POST /api/llm/start_session/
Content-Type: application/json

{
  "room_uuid": "채팅방-UUID"
}
```

**응답:**
```json
{
  "result": "success",
  "session_id": "생성된-세션-UUID",
  "room_uuid": "채팅방-UUID",
  "room_name": "채팅방 이름",
  "message": "AI 세션이 생성되었습니다."
}
```

### 2. AI 세션 목록 조회
```http
GET /api/llm/sessions/
```

**응답:**
```json
{
  "result": "success",
  "sessions": [
    {
      "session_id": "세션-UUID",
      "room_uuid": "채팅방-UUID",
      "room_name": "채팅방 이름",
      "created_at": "2025-12-02T..."
    }
  ],
  "total_count": 1
}
```

## 🔌 WebSocket 연결

### URL 패턴
```
ws://127.0.0.1:8000/ws/llm/{session_id}/
```

### 프론트엔드 → 백엔드

**채팅 메시지 전송:**
```json
{
  "type": "chat_message",
  "message": "사용자 메시지"
}
```

### 백엔드 → 프론트엔드

**1. 채팅 메시지 (사용자/AI):**
```json
{
  "type": "chat_message",
  "message": "메시지 내용",
  "username": "사용자명 또는 AI_Assistant",
  "message_id": 123,
  "timestamp": "2025-12-02T...",
  "is_self": true/false,
  "is_ai": true/false
}
```

**2. AI 참여 알림:**
```json
{
  "type": "ai_joined",
  "username": "AI_Assistant",
  "message": "AI_Assistant가 대화에 참여했습니다.",
  "timestamp": "2025-12-02T..."
}
```

**3. AI 생각 중:**
```json
{
  "type": "ai_thinking",
  "username": "AI_Assistant"
}
```

**4. AI 에러:**
```json
{
  "type": "ai_error",
  "message": "AI 응답 생성 중 오류가 발생했습니다."
}
```

## 🔄 메시지 흐름

1. **사용자 메시지 전송**
   - 프론트: `{type: "chat_message", message: "안녕"}`
   - Consumer: 메시지 저장 → 브로드캐스트
   - 모든 연결: 사용자 메시지 수신

2. **AI 응답 생성**
   - Consumer: AI 생각 중 표시 전송
   - Consumer: 최근 10개 메시지 조회
   - Consumer: OpenAI API 호출 (system persona + 히스토리 + 새 메시지)
   - Consumer: AI 응답 저장 → 브로드캐스트
   - 모든 연결: AI 응답 수신

## 🎨 AI 페르소나

```python
{
  "role": "system",
  "content": "당신은 개발자 채팅방에 참여한 친절하고 전문적인 AI 어시스턴트입니다. 항상 한국어로 답변하며, 코드 관련 질문에는 구체적이고 실용적인 조언을 제공합니다."
}
```

## ⚙️ 설정 필요 사항

### 1. 환경 변수 (.env)
```bash
OPENAI_API_KEY=sk-...
```

### 2. 마이그레이션 실행
```bash
cd server
python manage.py makemigrations llm
python manage.py migrate llm
```

### 3. 컨테이너 재시작
```bash
docker-compose restart web
```

## 🔍 디버깅

모든 로그는 `[AI_DEBUG]`, `[AI_ERROR]`, `[AI_SUCCESS]` 접두사로 필터링 가능:

```bash
# AI 관련 로그만 보기
docker-compose logs web | grep "\[AI_"

# 실시간 AI 로그 모니터링
docker-compose logs -f web | grep "\[AI_"
```

## ✅ 테스트 시나리오

### 1. AI 세션 생성
```javascript
// 1. 채팅방 UUID 얻기
const roomResponse = await fetch('http://127.0.0.1:8000/api/chat/my-rooms/', {
  credentials: 'include'
});
const roomData = await roomResponse.json();
const roomUuid = roomData.rooms[0].id;

// 2. AI 세션 생성
const sessionResponse = await fetch('http://127.0.0.1:8000/api/llm/start_session/', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  credentials: 'include',
  body: JSON.stringify({room_uuid: roomUuid})
});
const sessionData = await sessionResponse.json();
console.log('Session ID:', sessionData.session_id);
```

### 2. WebSocket 연결 및 대화
```javascript
const sessionId = sessionData.session_id;
const ws = new WebSocket(`ws://127.0.0.1:8000/ws/llm/${sessionId}/`);

ws.onopen = () => {
  console.log('AI 세션 연결됨');
  
  // 메시지 전송
  ws.send(JSON.stringify({
    type: 'chat_message',
    message: 'Django에서 비동기 처리하는 방법 알려줘'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`[${data.type}] ${data.username}: ${data.message}`);
};
```

## 🐛 알려진 이슈 및 TODO

- [ ] OPENAI_API_KEY 검증 추가
- [ ] AI 세션 비활성화 기능 구현
- [ ] 토큰 사용량 추적
- [ ] 비용 모니터링
- [ ] 메시지 레이트 리미팅
- [ ] AI 응답 스트리밍 (현재는 전체 응답 대기)

## 📚 참고 사항

- AI 채팅은 일반 채팅과 완전히 분리된 별도 세션
- 동일한 ChatRoom에 여러 AI 세션 생성 가능
- AI 메시지도 Message 테이블에 저장 (sender=AI_Assistant)
- 최근 10개 메시지만 컨텍스트로 사용 (토큰 제한)
