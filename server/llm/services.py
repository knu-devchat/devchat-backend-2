from openai import AsyncOpenAI 
from django.conf import settings 
import asyncio

# OpenAI 비동기 클라이언트 초기화
client = AsyncOpenAI(api_key=getattr(settings, 'OPENAI_API_KEY', None))

async def get_ai_response(full_message_history: list) -> str:
    """
    OpenAI API를 비동기적으로 호출하여 AI 응답을 반환합니다.
    
    Args:
        full_message_history: OpenAI 형식의 메시지 히스토리
                             [{"role": "system/user/assistant", "content": "..."}]
    
    Returns:
        str: AI 응답 텍스트
    """
    try:
        print(f"[AI_SERVICE] OpenAI API 호출 시작 - 메시지 수: {len(full_message_history)}")
        
        # API 키 확인
        if not settings.OPENAI_API_KEY:
            print(f"[AI_SERVICE ERROR] OPENAI_API_KEY가 설정되지 않음")
            return "죄송합니다. AI 서비스가 설정되지 않았습니다. 관리자에게 문의해주세요."
        
        # OpenAI API 호출
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=full_message_history,
            temperature=0.7,
            max_tokens=1000,
            timeout=15.0  # 타임아웃 설정
        )
        
        # 응답 텍스트 추출
        ai_message = response.choices[0].message.content
        
        print(f"[AI_SERVICE] OpenAI API 응답 성공 - 길이: {len(ai_message)}자")
        
        return ai_message
        
    except asyncio.TimeoutError:
        print(f"[AI_SERVICE ERROR] API 호출 타임아웃")
        return "죄송합니다. AI 응답 생성 시간이 초과되었습니다. 다시 시도해주세요."
        
    except Exception as e:
        print(f"[AI_SERVICE ERROR] API 호출 중 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        return "죄송합니다. AI 서비스에 연결할 수 없거나 요청 처리 중 문제가 발생했습니다."
