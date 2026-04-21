import sqlite3
import os
import chromadb
import config
from bs4 import BeautifulSoup
from google import genai
from google.genai import types

# 1. API 및 DB 설정
client = genai.Client(api_key=config.GEMINI_API_KEY)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_DB_PATH = os.path.join(BASE_DIR, 'data', 'tracker.db')
CHROMA_DB_PATH = os.path.join(BASE_DIR, 'data', 'chroma_db')

# 2. ChromaDB 초기화 (로컬 디스크에 저장)
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
collection = chroma_client.get_or_create_collection(name="boj_problems")

def clean_html(raw_html):
    """HTML 태그를 제거하고 순수 텍스트만 추출합니다."""
    if not raw_html: return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator=" ", strip=True)

def build_vector_db():
    print("🚀 Vector DB 구축을 시작합니다...")
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    
    # 💡 문제를 조인하여 가져옵니다 (problems 테이블이 있다고 가정)
    cursor.execute("""
        SELECT p.problem_id, p.title, p.tier, p.tags, 
               d.description, d.input_desc, d.output_desc
        FROM problems p
        JOIN problem_details d ON p.problem_id = d.problem_id
        WHERE d.description IS NOT NULL
    """)
    rows = cursor.fetchall()
    
    # ChromaDB API는 배치(Batch)로 한 번에 넣는 것이 효율적입니다.
    ids = []
    documents = []
    metadatas = []
    
    for row in rows:
        p_id, title, tier, tags, desc, inp, out = row
        
        # 1. 텍스트 정제
        clean_desc = clean_html(desc)
        clean_inp = clean_html(inp)
        clean_out = clean_html(out)
        
        # 2. 임베딩할 문서(Document) 조합
        # LLM이 문제의 핵심 의미를 잘 파악하도록 압축합니다.
        document_text = f"[문제: {title}]\n{clean_desc}\n[입력조건]: {clean_inp}\n[입력조건]: {clean_out}"
        
        # 3. 메타데이터(Metadata) 구성
        meta = {
            "problem_id": p_id,
            "title": title,
            "tier": str(tier),
            "tags": str(tags)
        }
        
        ids.append(str(p_id))
        documents.append(document_text[:8000])
        metadatas.append(meta)
        
        # 메모리 관리를 위해 100개씩 끊어서 업로드 (Chunking)
        if len(ids) >= 100:
            _embed_and_store(ids, documents, metadatas)
            ids, documents, metadatas = [], [], []
            
    # 남은 데이터 처리
    if ids:
        _embed_and_store(ids, documents, metadatas)
        
        print("🎉 Vector DB 구축이 완료되었습니다!")
    else:
        conn.close()

def _embed_and_store(ids, documents, metadatas):
    """Google 임베딩 API 호출 및 ChromaDB 저장"""
    try:
        # Google API로 텍스트들을 768차원 벡터로 변환
        response = client.models.embed_content(
            model='gemini-embedding-001',
            contents=documents
        )
        # 반환된 벡터 리스트 추출
        embeddings = [emb.values for emb in response.embeddings]
        
        # ChromaDB에 밀어넣기
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        print(f"✅ {len(ids)}개 문서 벡터화 및 저장 완료")
    except Exception as e:
        print(f"❌ 임베딩 에러: {e}")

if __name__ == "__main__":
    build_vector_db()