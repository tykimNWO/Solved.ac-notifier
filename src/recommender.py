import os
import chromadb
from google import genai
from google.genai import types
import config
from src.database import DatabaseManager
import json

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

def analyze_intent_and_rewrite(message: str, history: list) -> tuple[bool, str, str]:
    """
    과거 대화를 바탕으로 사용자의 의도를 파악하고, ChromaDB에 던질 검색어를 정제합니다.
    """
    # 1차 방어선 (명시적 키워드 우선순위)
    review_keywords = ["풀었던", "복습", "다시", "기존에", "풀어본", "저번에", "아까"]
    is_explicit_review = any(keyword in message for keyword in review_keywords)
    
    # 최근 대화 6개 정도만 집중적으로 참고
    history_text = "\n".join([f"{msg['role']}: {msg['text']}" for msg in history[-6:]])
    
    prompt = f"""
    당신은 사용자의 대화 맥락을 추적하고 최적의 검색 쿼리를 생성하는 의도 분석기입니다.
    
    [핵심 지침: 세션 모드 유지 및 CoT]
    1. 사용자가 이전 대화에서 '복습(review)'을 원했다면, "다른 거", "더 추천해줘"라는 질문에도 **반드시 'review' 상태를 유지**해야 합니다.
    2. 명시적으로 "이제 안 푼 거 줘", "새로운 문제", "다른 유형의 신규 문제"라고 해야만 'new'로 바뀝니다.
    3. 근거 없는 구체화(예: 말하지 않은 골드 5 티어 추가)는 절대 금지입니다.
    
    [대화 이력]
    {history_text}
    
    [현재 질문]
    user: {message}
    
    [작업 지침]
    - 반드시 `reasoning` 필드를 가장 먼저 작성하여 이전 대화의 모드가 무엇이었는지, 현재 질문에서 모드 변경이 감지되었는지 스스로 논리적으로 생각한 후 `intent`를 결정하세요.
    
    [출력 형식 (반드시 JSON만)]
    {{
        "reasoning": "이전 대화에서 사용자가 '기존에 풀었던(review)' 문제를 요청했음. 현재 '다른 문제'를 요구하지만 모드 변경을 명시하지 않았으므로 복습 모드를 유지함.",
        "intent": "review",
        "search_query": "그리디 알고리즘"
    }}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-3.1-flash-lite-preview',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1 # 일관성을 위해 낮은 온도로 설정
            )
        )
        result = json.loads(response.text)
        
        reasoning = result.get('reasoning', '이전 맥락을 분석하여 적절한 검색 의도를 파악했습니다.')
        # LLM의 추론 과정을 로그로 출력 (디버깅용)
        print(f"🧠 [LLM의 추론 과정]: {reasoning}")
        
        # 명시적 키워드가 있거나 LLM이 review라고 판단한 경우 복습 모드 유지
        if is_explicit_review:
            exclude_solved = False
        else:
            exclude_solved = (result.get("intent") != "review")
            
        refined_query = result.get("search_query", message)
        return exclude_solved, refined_query, reasoning
        
    except Exception as e:
        print(f"⚠️ 의도 분석 실패, 기본값 진행: {e}")
        return not is_explicit_review, message, "대화 이력을 참고하여 추천을 진행합니다."

def retrieve_similar_problems(query: str, solved_ids: list, exclude_solved: bool, blacklist_ids: list = [], top_k: int = 3):
    try:
        # 💡 [핵심 예외 처리] 복습을 원하는데 tracker.db에 푼 문제가 없을 때!
        if not exclude_solved and len(solved_ids) == 0:
            return "학습자님이 아직 시스템에 기록한 푼 문제(Solved) 이력이 없습니다. 먼저 새로운 문제를 풀고 기록을 남겨주셔야 복습 추천이 가능합니다."

        # 질문 임베딩 (기존 로직)
        response = client.models.embed_content(model='gemini-embedding-001', contents=query)
        query_embedding = response.embeddings[0].values
        
        # ChromaDB 필터링 (동적 조건 적용)
        conditions = []
        
        # 1. 푼 문제 관련 조건 (복습 vs 신규)
        if solved_ids:
            if exclude_solved:
                conditions.append({"problem_id": {"$nin": solved_ids}}) # 안 푼 문제만
            else:
                conditions.append({"problem_id": {"$in": solved_ids}})  # 푼 문제만
        
        # 2. 최근 추천 리스트 제외 (블랙리스트)
        if blacklist_ids:
            conditions.append({"problem_id": {"$nin": blacklist_ids}})
            
        # 조건 결합 (ChromaDB $and 연산)
        where_clause = None
        if len(conditions) > 1:
            where_clause = {"$and": conditions}
        elif len(conditions) == 1:
            where_clause = conditions[0]
                
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_clause
        )
        
        # 검색 결과가 아예 비어있을 때의 환각 방지
        if not results or not results['documents'] or not results['documents'][0]:
            return "조건에 맞는 문제를 데이터베이스에서 찾을 수 없습니다."

        retrieved_docs = results['documents'][0]
        context = "\n\n---\n\n".join(retrieved_docs)
        return context
        
    except Exception as e:
        print(f"❌ 검색 에러: {e}")
        return ""

def stream_chat_response(message: str, history: list=[]):
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

    # 0.5. 최근 대화에서 추천된 문제 번호 추출 (블랙리스트)
    # 프론트엔드에서 태그를 파싱하고 지울 수 있으므로, DB에 저장된 원본 메시지에서 추출하는 것이 가장 정확합니다.
    import re
    blacklist_ids = []
    
    # DB에서 최근 추천된 모든 문제 ID 추출
    try:
        raw_history = db.get_chat_history(limit=50)
        for msg in raw_history:
            if msg['role'] == 'ai':
                matches = re.findall(r"\[LOAD_PROBLEM:(\d+)\]", msg['text'])
                blacklist_ids.extend([int(m) for m in matches])
    except Exception as e:
        print(f"⚠️ 블랙리스트 추출 중 오류 (기존 history 참고): {e}")
        # DB 실패 시 전달받은 history에서라도 추출 시도
        for msg in history:
            if msg['role'] == 'ai':
                matches = re.findall(r"\[LOAD_PROBLEM:(\d+)\]", msg['text'])
                blacklist_ids.extend([int(m) for m in matches])
    
    # 중복 제거
    blacklist_ids = list(set(blacklist_ids))
    
    # 1. 문서 검색 (Retrieval)
    exclude_solved, refined_query, reasoning = analyze_intent_and_rewrite(message, history)

    # 1.5. 프론트엔드에 사고 과정 먼저 전달
    yield f"[THOUGHT]\n{reasoning}\n[/THOUGHT]\n\n"

    status_msg = "푼 문제 제외" if exclude_solved else "푼 문제 포함(복습)"
    if blacklist_ids:
        print(f"🚫 최근 추천된 {len(blacklist_ids)}개 문제(ID: {blacklist_ids})는 검색에서 제외합니다.")

    print(f"🔍 [Query Rewritten] 정제된 검색어: '{refined_query}' ({status_msg})")
    
    retrieved_context = retrieve_similar_problems(
        query=refined_query, 
        solved_ids=solved_ids, 
        exclude_solved=exclude_solved,
        blacklist_ids=blacklist_ids
    )
    
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