from openai import AsyncOpenAI 
from django.conf import settings 
import asyncio

# 1. 클라이언트 초기화: settings에서 확인된 API 키를 사용하여 비동기 클라이언트 생성
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) 


async def get_ai_response(prompt: str) -> str:
    """사용자의 프롬프트를 받아 OpenAI API를 비동기적으로 호출하고 텍스트 응답을 반환합니다."""
    
    try:
        #API 호출
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo", # 원하는 모델 지정
            messages=[
                {"role": "system", "content": "당신은 채팅방에 참여한 친절하고 유용한 AI 어시스턴트입니다. 항상 한국어로 대답해주세요."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            # 네트워크 타임아웃을 설정하여 Channels 서버가 너무 오래 대기하지 않도록 방지
            timeout=15.0
        )
        
        #응답 텍스트 추출 및 반환
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"[OpenAI ERROR] API 호출 중 예외 발생: {e}")
        return "죄송합니다. AI 서비스에 연결할 수 없거나 요청 처리 중 문제가 발생했습니다."