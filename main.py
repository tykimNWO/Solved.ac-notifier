import os
import json
import time
import sqlite3
import subprocess
import tempfile
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from fastapi.responses import StreamingResponse
from src.recommender import stream_chat_response

# 💡 DB 경로 설정 (에러 방지를 위한 절대 경로)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'tracker.db') # data 폴더 안에 있다고 가정

# FastAPI 앱 생성
app = FastAPI(title="AI Tutor API", description="Solved.ac Notifier 백엔드 서버")

# 💡 CORS 설정 (React의 5173 포트에서 오는 요청을 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------
# 📌 1. 데이터 모델 정의 (Pydantic) - 들어오는 요청의 형태를 검증
# ----------------------------------------------------
class ChatRequest(BaseModel):
    message: str

class JudgeRequest(BaseModel):
    problem_id: int
    code: str

# ----------------------------------------------------
# 📌 2. API 엔드포인트 구현
# ----------------------------------------------------

@app.get("/")
def read_root():
    return {"status": "ok", "message": "AI Tutor API Server is running."}

@app.post("/api/chat/stream")
async def chat_with_ai_stream(req: ChatRequest):
    """Gemini의 응답을 실시간으로 프론트엔드에 스트리밍합니다."""
    print(f"📥 [User Message]: {req.message}")
    
    # 스트리밍 제너레이터를 FastAPI의 StreamingResponse에 담아서 반환
    return StreamingResponse(
        stream_chat_response(req.message), 
        media_type="text/plain" # 순수 텍스트 스트림 형태로 전송
    )

@app.get("/api/problem/{problem_id}")
async def get_problem(problem_id: int):
    """DB에서 문제 상세 정보를 가져오는 API"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT description, input_desc, output_desc, sample_inputs, sample_outputs, problem_limit
            FROM problem_details 
            WHERE problem_id = ?
        """, (problem_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "status": "success",
                "data": {
                    "description": row[0],
                    "input_desc": row[1],
                    "output_desc": row[2],
                    "sample_inputs": json.loads(row[3]) if row[3] else [],
                    "sample_outputs": json.loads(row[4]) if row[4] else [],
                    "problem_limit": row[5] or "",
                }
            }
        else:
            raise HTTPException(status_code=404, detail="DB에 해당 문제가 없습니다.")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/judge")
async def run_judge(req: JudgeRequest):
    """사용자의 파이썬 코드를 채점하는 API"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT sample_inputs, sample_outputs FROM problem_details WHERE problem_id = ?", (req.problem_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="채점 데이터를 찾을 수 없습니다.")
        
        sample_inputs = json.loads(row[0])
        sample_outputs = json.loads(row[1])
        results = []

        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode='w', encoding='utf-8') as f:
            f.write(req.code)
            temp_code_path = f.name

        for i in range(len(sample_inputs)):
            start_time = time.time()
            try:
                process = subprocess.run(
                    ["python3", temp_code_path],
                    input=sample_inputs[i],
                    capture_output=True,
                    text=True,
                    timeout=2.0 
                )
                
                elapsed_time = (time.time() - start_time) * 1000
                actual_output = process.stdout.strip()
                expected_output = sample_outputs[i].strip()

                if process.returncode != 0:
                    res = {"case": i+1, "result": "Runtime Error", "error": process.stderr}
                elif actual_output == expected_output:
                    res = {"case": i+1, "result": "Success", "time": f"{elapsed_time:.1f}ms"}
                else:
                    res = {"case": i+1, "result": "Wrong Answer", "actual": actual_output, "expected": expected_output}
                    
            except subprocess.TimeoutExpired:
                res = {"case": i+1, "result": "Time Limit Exceeded"}
            
            results.append(res)

        os.remove(temp_code_path)
        return {"status": "success", "results": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# main.py 에 추가 및 수정할 내용

# 1. 메모 요청 모델 추가
class MemoRequest(BaseModel):
    problem_id: int
    content: str

# 2. 서버 시작 시 테이블 생성 로직 (앱 하단이나 초기화 부분에 추가)
@app.on_event("startup")
def setup_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # 메모 테이블 생성 (문제 번호를 PK로 하여 1:1 대응)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memos (
            problem_id INTEGER PRIMARY KEY,
            content TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # problem_details에 제한(시간/메모리) HTML 컬럼이 없으면 추가 (기존 DB 호환)
    try:
        cursor.execute("ALTER TABLE problem_details ADD COLUMN problem_limit TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

# 3. 메모 조회 API
@app.get("/api/memo/{problem_id}")
async def get_memo(problem_id: int):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM memos WHERE problem_id = ?", (problem_id,))
        row = cursor.fetchone()
        conn.close()
        return {"status": "success", "content": row[0] if row else ""}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 4. 메모 저장 API
@app.post("/api/memo")
async def save_memo(req: MemoRequest):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # INSERT OR REPLACE를 사용하여 기존 메모가 있으면 업데이트
        cursor.execute("""
            INSERT OR REPLACE INTO memos (problem_id, content, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (req.problem_id, req.content))
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # main.py 파일 안의 app 객체를 실행하며, 코드가 바뀔 때마다 자동 재시작(reload=True)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)