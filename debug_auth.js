// ========================================
// 간단한 인증 확인 스크립트
// ========================================
console.log('🔍 인증 상태 확인 중...\n');

// 1. 쿠키 확인
console.log('📋 현재 쿠키:');
console.log(document.cookie || '(없음)');
console.log('');

// 2. API 호출 테스트
console.log('📋 API 테스트 중...');
const response = await fetch('http://127.0.0.1:8000/api/chat/my-rooms/', {
    credentials: 'include'
});

console.log('응답 정보:');
console.log('  - Status:', response.status);
console.log('  - Content-Type:', response.headers.get('content-type'));
console.log('  - URL:', response.url);
console.log('');

// 3. 응답 본문 확인
const text = await response.text();
console.log('응답 본문 (처음 200자):');
console.log(text.substring(0, 200));
console.log('');

// 4. JSON 파싱 시도
try {
    const data = JSON.parse(text);
    console.log('✅ JSON 파싱 성공:');
    console.log(data);
} catch (e) {
    console.error('❌ JSON 파싱 실패:', e.message);
    console.log('');
    console.log('해결 방법:');
    console.log('1. http://127.0.0.1:8000/login/github/ 접속하여 로그인');
    console.log('2. 로그인 후 다시 이 스크립트 실행');
}
