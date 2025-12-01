# 🧪 LLM AI Chat 테스트 결과

## ✅ 완료된 테스트

### 1. 데이터베이스 마이그레이션
```bash
✅ python manage.py makemigrations llm
✅ python manage.py migrate llm
✅ AiChatSession 모델 생성 완료
```

### 2. 앱 등록 확인
```bash
✅ INSTALLED_APPS에 'llm' 추가
✅ server/urls.py에 'api/llm/' 경로 추가
✅ server/asgi.py에 WebSocket 라우팅 추가
```

### 3. 모델 로드 테스트
```python
✅ LLM 앱 정상 로드: AiChatSession
✅ Consumer 로드 성공: AiChatConsumer
✅ WebSocket 패턴: ws/llm/<str:session_id>/
```

### 4. API 엔드포인트 테스트

#### 📋 테스트 데이터 생성
```
✅ 사용자 생성: testuser
✅ 채팅방 생성: AI_Test_Room
   UUID: 96dc6551-0337-4089-ba92-ddf79581a08f
```

#### 🔌 POST /api/llm/start_session/
```json
Request:
{
  "room_uuid": "96dc6551-0337-4089-ba92-ddf79581a08f"
}

Response (201):
{
  "result": "success",
  "session_id": "e1692be2-9d48-4bd6-8e8d-cd816e1b3fc8",
  "room_uuid": "96dc6551-0337-4089-ba92-ddf79581a08f",
  "room_name": "AI_Test_Room",
  "message": "AI 세션이 생성되었습니다."
}

✅ AI 세션 생성 성공
✅ 로그 출력 정상:
   [AI_API] ========== AI 세션 생성 요청 ==========
   [AI_API] 사용자: testuser
   [AI_API] 요청 데이터 확인
   [AI_API] 채팅방 조회 성공: AI_Test_Room
   [AI_API] 권한 확인 완료 - 방장: True
   [AI_API SUCCESS] ✅ AI 세션 생성 완료
```

#### 📊 DB 확인
```
✅ 총 1개 AI 세션 저장됨
   - Session: e1692be2... (Room: AI_Test_Room)
```

## 🔜 다음 테스트 (실제 환경에서 수행 필요)

### 1. WebSocket 연결 테스트

**방법 1: 브라우저 콘솔에서 테스트**
1. http://127.0.0.1:8000 접속
2. GitHub 로그인
3. 브라우저 콘솔 열기 (F12)
4. 아래 스크립트 붙여넣기:

```javascript
// 1. AI 세션 생성
const response = await fetch('http://127.0.0.1:8000/api/llm/start_session/', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    credentials: 'include',
    body: JSON.stringify({room_uuid: '96dc6551-0337-4089-ba92-ddf79581a08f'})
});
const data = await response.json();
console.log('Session ID:', data.session_id);

// 2. WebSocket 연결
const ws = new WebSocket(`ws://127.0.0.1:8000/ws/llm/${data.session_id}/`);

ws.onopen = () => {
    console.log('✅ WebSocket 연결 성공!');
    
    // 메시지 전송
    ws.send(JSON.stringify({
        type: 'chat_message',
        message: '안녕하세요, AI!'
    }));
};

ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    console.log(`[${msg.type}] ${msg.username}: ${msg.message}`);
};

window.testWs = ws; // 전역 저장
```

**방법 2: 테스트 스크립트 사용**
```bash
# 프로젝트 루트의 test_llm.js 파일 내용을 브라우저 콘솔에 붙여넣기
# 자동으로 전체 플로우 테스트
```

### 2. 메시지 타입별 테스트

#### ✅ 기대되는 WebSocket 메시지 흐름:

**1) 연결 시:**
```json
{
  "type": "ai_joined",
  "username": "AI_Assistant",
  "message": "AI_Assistant가 대화에 참여했습니다.",
  "timestamp": "2025-12-02T..."
}
```

**2) 사용자 메시지 전송 후:**
```json
// 사용자 메시지 에코백
{
  "type": "chat_message",
  "message": "안녕하세요!",
  "username": "testuser",
  "message_id": 1,
  "timestamp": "2025-12-02T...",
  "is_self": true,
  "is_ai": false
}

// AI 생각 중 표시
{
  "type": "ai_thinking",
  "username": "AI_Assistant"
}

// AI 응답 (OPENAI_API_KEY 설정 시)
{
  "type": "chat_message",
  "message": "안녕하세요! 무엇을 도와드릴까요?",
  "username": "AI_Assistant",
  "message_id": 2,
  "timestamp": "2025-12-02T...",
  "is_self": false,
  "is_ai": true
}
```

**3) OPENAI_API_KEY 미설정 시:**
```json
{
  "type": "chat_message",
  "message": "죄송합니다. AI 서비스가 설정되지 않았습니다. 관리자에게 문의해주세요.",
  "username": "AI_Assistant",
  "is_ai": true
}
```

### 3. OpenAI API 통합 테스트

#### 환경 변수 설정 (.env 파일 또는 docker-compose.yml)
```bash
OPENAI_API_KEY=sk-proj-...your-key...
```

#### 테스트 시나리오:
1. API 키 설정
2. 컨테이너 재시작: `docker-compose restart web`
3. WebSocket 연결
4. 메시지 전송: "Django에서 비동기 처리하는 방법 알려줘"
5. AI 응답 확인

#### 예상 동작:
- 사용자 메시지 즉시 브로드캐스트
- AI 생각 중 표시
- 최근 10개 메시지 컨텍스트로 OpenAI API 호출
- AI 응답 브로드캐스트 (한국어로)

### 4. 로그 모니터링 테스트

```bash
# AI 관련 로그만 실시간 모니터링
docker-compose logs -f web | grep "\[AI_"

# 기대되는 로그:
# [AI_DEBUG] ========== AI WebSocket 연결 시도 ==========
# [AI_DEBUG] User: testuser
# [AI_DEBUG] Is authenticated: True
# [AI_DEBUG] 추출된 Session ID: 'e1692be2...'
# [AI_DEBUG] 사용자 프로필: testuser
# [AI_DEBUG] AI 세션 확인 완료 - 기반 방: AI_Test_Room
# [AI_DEBUG] AI 프로필 로드: AI_Assistant
# [AI_SUCCESS] ✅ AI WebSocket 연결 성공
# [AI_DEBUG] 사용자 메시지 처리: testuser → 안녕하세요!
# [AI_DEBUG] AI 응답 생성 시작...
# [AI_DEBUG] 대화 히스토리: 0개 메시지
# [AI_SERVICE] OpenAI API 호출 시작 - 메시지 수: 2
# [AI_SERVICE] OpenAI API 응답 성공 - 길이: 50자
# [AI_DEBUG] AI 응답 브로드캐스트 완료
```

## 📝 테스트 체크리스트

### 기본 기능
- [✅] 마이그레이션 성공
- [✅] 모델 로드 성공
- [✅] API 엔드포인트 동작
- [✅] AI 세션 생성
- [✅] DB 저장 확인
- [ ] WebSocket 연결 (브라우저 테스트 필요)
- [ ] 메시지 송수신 (브라우저 테스트 필요)
- [ ] AI 응답 생성 (OPENAI_API_KEY 필요)

### 에러 처리
- [ ] 인증 없이 접근 시 401
- [ ] 존재하지 않는 방 UUID → 404
- [ ] 권한 없는 방 접근 → 403
- [ ] 잘못된 session_id → 4003 close
- [ ] API 키 없을 때 에러 메시지
- [ ] API 타임아웃 처리

### 권한 검증
- [ ] 방장만 접근 가능
- [ ] 참가자만 접근 가능
- [ ] 비참가자 접근 거부

### 로깅
- [✅] [AI_DEBUG] 로그 출력
- [✅] [AI_ERROR] 로그 출력
- [✅] [AI_SUCCESS] 로그 출력

## 🚀 실전 배포 전 체크리스트

- [ ] OPENAI_API_KEY 환경 변수 설정
- [ ] 프론트엔드 UI 구현
- [ ] 토큰 사용량 모니터링
- [ ] 비용 알림 설정
- [ ] 레이트 리미팅 구현
- [ ] 메시지 길이 제한 확인 (2000자)
- [ ] AI 응답 스트리밍 고려
- [ ] 에러 처리 UX 개선
- [ ] 세션 만료 로직
- [ ] 대화 히스토리 제한 (현재 10개)

## 📚 참고 문서

- API 문서: `LLM_IMPLEMENTATION.md`
- 테스트 스크립트: `test_llm.js`
- Consumer 코드: `server/llm/consumers.py`
- Views 코드: `server/llm/views.py`
