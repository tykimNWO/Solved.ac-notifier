import os
import chromadb
from google import genai
from google.genai import types
import config
from src.database import DatabaseManager

# 1. API 클라이언트 초기화
client = genai.Client(api_key=config.GEMINI_API_KEY)

# 2. DB 및 ChromaDB 연동
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'data', 'tracker.db')
db = DatabaseManager(DB_PATH)

CHROMA_DB_PATH = os.path.join(BASE_DIR, 'data', 'chroma_db')
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
collection = chroma_client.get_or_create_collection(name="boj_problems")

# 💡 태영님만을 위한 초개인화 시스템 프롬프트
SYSTEM_INSTRUCTION = """당신은 김태영님의 전담 알고리즘 및 코딩 튜터입니다.
학습자는 현재 은행의 AI데이터전략부에서 근무 중인 데이터 기획자이자 엔지니어이며,
기회비용과 정확성, 실무적 운영성을 매우 중요하게 생각하는 분석적이고 계획적인 성향입니다.
항상 신사적이고 매너 있는 어조를 유지하세요.

[중요 지시사항]
1. 사용자가 문제 추천을 요청하면, 제공된 <검색된_문제_목록>을 반드시 참고하여 가장 적합한 1문제를 골라 추천하세요.
2. 단순히 문제 번호만 주지 말고, 이 문제가 왜 현재 시점에 풀기 좋은지 기회비용과 알고리즘 컨셉(시간/공간 복잡도) 관점에서 논리적으로 설명하세요.
3. 문제를 추천한 뒤에는 문제 풀이에 진입할 수 있도록 답변 가장 마지막 줄에 정확히 [LOAD_PROBLEM:문제번호] 형식의 특수 태그를 추가하세요. (예: [LOAD_PROBLEM:1005])
"""

def retrieve_similar_problems(query: str, solved_ids: list = None, exclude_solved: bool = True, top_k: int = 3):
    """
    사용자 질문을 벡터화하여 ChromaDB에서 유사한 문제를 찾아옵니다.
    exclude_solved가 True이면 이미 푼 문제는 제외합니다.
    """
    try:
        # 질문을 임베딩
        response = client.models.embed_content(
            model='gemini-embedding-001',
            contents=query
        )
        query_embedding = response.embeddings[0].values
        
        # 필터 설정
        where_filter = None
        if solved_ids and exclude_solved:
            where_filter = {"problem_id": {"$nin": solved_ids}}
        
        # ChromaDB 검색
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter
        )
        
        # 검색된 문서들을 하나의 문자열로 결합
        if results and results['documents'] and results['documents'][0]:
            retrieved_docs = results['documents'][0]
            context = "\n\n---\n\n".join(retrieved_docs)
            return context
        return "검색된 문제가 없습니다."
    except Exception as e:
        print(f"❌ 검색 에러: {e}")
        return ""

def stream_chat_response(message: str):
    """RAG 파이프라인을 실행하고 결과를 실시간으로 반환합니다."""
    print(f"🚀 [RAG 시작] 질문: {message}")
    
    # 0. 사용자 정보 및 의도 파악
    solved_ids = db.get_solved_problem_ids()
    user_stats = db.get_latest_user_stats()
    
    # 사용자가 '다시', '복습', '풀었던' 등의 키워드를 사용했는지 확인
    review_keywords = ["복습", "다시", "풀었던", "이미 푼", "review", "again", "solved"]
    is_review_request = any(keyword in message for keyword in review_keywords)
    
    user_context = ""
    if user_stats:
        user_context = f"\n[학습자 현재 상태]: 티어 {user_stats['tier']}, 레이팅 {user_stats['rating']}, 해결한 문제 수 {user_stats['solved_count']}, 스트릭 {user_stats['streak']}일"

    # 1. 문서 검색 (Retrieval)
    exclude_solved = not is_review_request
    status_msg = "푼 문제 제외" if exclude_solved else "푼 문제 포함(복습)"
    print(f"🔍 Vector DB에서 유사 문제 검색 중... ({status_msg})")
    
    retrieved_context = retrieve_similar_problems(message, solved_ids=solved_ids, exclude_solved=exclude_solved)
    
    # 2. 프롬프트 증강 (Augmentation)
    prompt_instruction = "목록에 있는 문제는 사용자가 아직 풀지 않은 유사한 문제들입니다." if exclude_solved else "목록에 있는 문제는 사용자가 이미 풀었거나 관련 있는 복습용 문제들입니다."
    
    augmented_prompt = f"""사용자의 질문에 답변하세요.
{user_context}

필요하다면 아래의 <검색된_문제_목록>을 참고하여 추천을 진행하세요.
{prompt_instruction}

<검색된_문제_목록>
{retrieved_context}
</검색된_문제_목록>

사용자 질문: {message}
"""
    
    # 3. 모델 생성 (Generation)
    model_id = 'gemini-3.1-flash-lite-preview' 
    generation_config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        temperature=0.7,
    )

    try:
        response = client.models.generate_content_stream(
            model=model_id,
            contents=augmented_prompt,
            config=generation_config
        )

        for chunk in response:
            if chunk.text:
                yield chunk.text
                
    except Exception as e:
        yield f"\n[AI 엔진 연결 오류]: {str(e)}"