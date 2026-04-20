import os
from google import genai
from google.genai import types
import config  # API 키가 저장된 파일이라고 가정합니다.

# 최신 SDK 클라이언트 초기화
client = genai.Client(api_key=config.GEMINI_API_KEY)

# 💡 태영님만을 위한 초개인화 시스템 프롬프트
SYSTEM_INSTRUCTION = """당신은 김태영님의 전담 알고리즘 및 코딩 튜터입니다.
학습자는 현재 은행의 AI데이터전략부에서 근무 중인 데이터 기획자이자 엔지니어이며,
기회비용과 정확성, 실무적 운영성을 매우 중요하게 생각하는 분석적이고 계획적인 성향입니다.
따라서 다음과 같은 규칙을 엄격히 준수하여 답변하세요:
1. 항상 신사적이고 매너 있는 어조를 유지하세요.
2. 단순히 코드 정답만 툭 던져주는 것을 지양하고, 시간/공간 복잡도 측면에서 왜 이 로직이 효율적인지 논리적인 프레임워크를 제공하세요.
3. 문제가 막혔을 때는 스스로 해결할 수 있도록 핵심 힌트와 엣지 케이스를 먼저 제시하세요.
"""

def stream_chat_response(message: str):
    """Gemini API를 호출하고 응답을 실시간으로 Yield하는 제너레이터 함수"""
    print(f"🚀 [Gemini] 스트리밍 추론 시작: {message}")
    
    # 모델은 가장 빠르고 추론력이 뛰어난 2.5-flash 또는 3.1-flash-lite를 사용합니다.
    model_id = 'gemini-3.1-flash-lite-preview' 
    
    generation_config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        temperature=0.7,
    )

    try:
        # 스트리밍 API 호출
        response = client.models.generate_content_stream(
            model=model_id,
            contents=message,
            config=generation_config
        )

        # 텍스트 조각(chunk)이 도착할 때마다 실시간으로 반환(yield)
        for chunk in response:
            if chunk.text:
                yield chunk.text
                
    except Exception as e:
        yield f"\n[AI 엔진 연결 오류]: {str(e)}"