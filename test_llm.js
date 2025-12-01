// ========================================
// LLM AI Chat 테스트 스크립트
// ========================================
// 브라우저 콘솔에서 실행하세요!
// http://127.0.0.1:8000 에 접속한 상태에서 실행

console.log('🤖 LLM AI Chat 테스트 시작...\n');

// ========================================
// 1단계: 로그인 확인
// ========================================
async function checkAuth() {
    console.log('📋 1단계: 인증 확인');
    const response = await fetch('http://127.0.0.1:8000/api/chat/my-rooms/', {
        credentials: 'include'
    });
    
    console.log('   응답 상태:', response.status);
    console.log('   Content-Type:', response.headers.get('content-type'));
    
    if (response.status === 401) {
        console.error('❌ 로그인이 필요합니다!');
        console.log('👉 http://127.0.0.1:8000/login/github/ 로 이동하여 로그인하세요.');
        return null;
    }
    
    if (response.status === 404) {
        console.error('❌ API 엔드포인트를 찾을 수 없습니다.');
        console.log('   URL 확인: /api/chat/my-rooms/');
        return null;
    }
    
    // HTML이 반환되는지 확인
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('text/html')) {
        console.error('❌ JSON 대신 HTML이 반환되었습니다.');
        console.log('   로그인 페이지로 리다이렉트되었을 수 있습니다.');
        console.log('👉 http://127.0.0.1:8000/login/github/ 로 이동하여 로그인하세요.');
        return null;
    }
    
    const data = await response.json();
    console.log('✅ 로그인 확인됨');
    console.log('   보유한 방:', data.rooms.length, '개\n');
    return data.rooms;
}

// ========================================
// 2단계: AI 세션 생성
// ========================================
async function createAISession(roomUuid) {
    console.log('📋 2단계: AI 세션 생성');
    console.log('   Room UUID:', roomUuid);
    
    const response = await fetch('http://127.0.0.1:8000/api/llm/start_session/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
            room_uuid: roomUuid
        })
    });
    
    if (!response.ok) {
        const error = await response.json();
        console.error('❌ AI 세션 생성 실패:', error);
        return null;
    }
    
    const data = await response.json();
    console.log('✅ AI 세션 생성 성공');
    console.log('   Session ID:', data.session_id);
    console.log('   Room Name:', data.room_name, '\n');
    return data.session_id;
}

// ========================================
// 3단계: WebSocket 연결 및 테스트
// ========================================
function testWebSocket(sessionId) {
    console.log('📋 3단계: WebSocket 연결');
    console.log('   ws://127.0.0.1:8000/ws/llm/' + sessionId + '/\n');
    
    const ws = new WebSocket(`ws://127.0.0.1:8000/ws/llm/${sessionId}/`);
    
    ws.onopen = () => {
        console.log('✅ WebSocket 연결 성공!\n');
        
        console.log('📤 테스트 메시지 전송: "안녕하세요!"');
        ws.send(JSON.stringify({
            type: 'chat_message',
            message: '안녕하세요!'
        }));
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        console.log(`📨 [${data.type}] 받음:`);
        
        if (data.type === 'chat_message') {
            const icon = data.is_ai ? '🤖' : '👤';
            console.log(`   ${icon} ${data.username}: ${data.message}`);
            console.log(`   - is_self: ${data.is_self}, is_ai: ${data.is_ai}`);
            console.log(`   - timestamp: ${data.timestamp}\n`);
        } else if (data.type === 'ai_joined') {
            console.log(`   🎉 ${data.message}\n`);
        } else if (data.type === 'ai_thinking') {
            console.log(`   💭 AI가 생각하는 중...\n`);
        } else if (data.type === 'ai_error') {
            console.log(`   ❌ ${data.message}\n`);
        }
    };
    
    ws.onerror = (error) => {
        console.error('❌ WebSocket 에러:', error);
    };
    
    ws.onclose = (event) => {
        console.log(`🔌 WebSocket 연결 종료 (code: ${event.code})`);
    };
    
    // 전역 변수로 저장
    window.aiWs = ws;
    console.log('💡 WebSocket을 window.aiWs에 저장했습니다.');
    console.log('💡 추가 메시지 전송: window.aiWs.send(JSON.stringify({type: "chat_message", message: "메시지"}))');
}

// ========================================
// 전체 테스트 실행
// ========================================
async function runFullTest() {
    try {
        // 1. 인증 확인
        const rooms = await checkAuth();
        if (!rooms || rooms.length === 0) {
            console.error('❌ 채팅방이 없습니다. 먼저 채팅방을 생성하세요.');
            return;
        }
        
        // 2. 첫 번째 방으로 AI 세션 생성
        const roomUuid = rooms[0].id;
        const sessionId = await createAISession(roomUuid);
        if (!sessionId) {
            return;
        }
        
        // 3. WebSocket 연결
        testWebSocket(sessionId);
        
    } catch (error) {
        console.error('❌ 테스트 실패:', error);
    }
}

// ========================================
// 테스트 시작!
// ========================================
console.log('========================================');
console.log('🚀 자동 테스트 시작...\n');
runFullTest();

console.log('========================================');
console.log('💡 수동 테스트 함수:');
console.log('   - checkAuth()              : 인증 확인');
console.log('   - createAISession(roomUuid): AI 세션 생성');
console.log('   - testWebSocket(sessionId) : WebSocket 연결');
console.log('   - runFullTest()            : 전체 자동 테스트');
console.log('========================================\n');
