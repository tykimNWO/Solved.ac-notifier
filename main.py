import os
import json
import sqlite3
from collections import Counter
from datetime import date, datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from fastapi.responses import StreamingResponse
from src.api_client import SolvedAcClient
from src.recommender import stream_chat_response
from src.database import DatabaseManager
from src.judge.aggregator import JudgeResultAggregator
from src.judge.gemini_hint import GeminiHintGenerator
from src.judge.types import HintRequestModel, HintResponseModel, JudgeMode
from src.services.rating.class_fetcher import get_or_fetch_class_problem_groups
from src.services.rating.formulas import calculate_local_ac_rating, calculate_tag_ratings

from typing import Any, Dict, List, Optional, Tuple

# 💡 DB 경로 설정 (에러 방지를 위한 절대 경로)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'tracker.db')
DATA_DIR = os.path.join(BASE_DIR, 'data')
DEFAULT_SOLVED_AC_HANDLE = "tykim0710"
db = DatabaseManager(DB_PATH)
judge_aggregator = JudgeResultAggregator(DB_PATH, DATA_DIR, db)
hint_generator = GeminiHintGenerator()

# FastAPI 앱 생성
app = FastAPI(title="Solved.ac-with-LLMCoach API", description="Solved.ac-with-LLMCoach 백엔드 서버")

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
class ChatMessage(BaseModel):
    role: str
    text: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = Field(default_factory=list)
    current_problem_id: Optional[int] = None

class JudgeRequest(BaseModel):
    problem_id: int
    code: str
    mode: JudgeMode = "basic"

DASHBOARD_TIER_GROUPS = ["Bronze", "Silver", "Gold", "Platinum", "Diamond", "Ruby", "Unknown"]
DASHBOARD_LEVELS = (
    [(0, "NR")]
    + [(level, f"B{6 - level}") for level in range(1, 6)]
    + [(level, f"S{11 - level}") for level in range(6, 11)]
    + [(level, f"G{16 - level}") for level in range(11, 16)]
    + [(level, f"P{21 - level}") for level in range(16, 21)]
    + [(level, f"D{26 - level}") for level in range(21, 26)]
    + [(level, f"R{31 - level}") for level in range(26, 31)]
)

def parse_logged_date(value: Any) -> Optional[date]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = str(value).strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    try:
        return datetime.strptime(raw[:10], "%Y-%m-%d").date()
    except ValueError:
        return None

def get_tier_name(level: Optional[int]) -> str:
    if not level or level <= 0:
        return "Unknown"
    if level <= 5:
        return f"Bronze {6 - level}"
    if level <= 10:
        return f"Silver {11 - level}"
    if level <= 15:
        return f"Gold {16 - level}"
    if level <= 20:
        return f"Platinum {21 - level}"
    if level <= 25:
        return f"Diamond {26 - level}"
    return f"Ruby {31 - level}"

def get_short_tier_name(level: Optional[int]) -> str:
    if not level or level <= 0:
        return "NR"
    if level <= 5:
        return f"B{6 - level}"
    if level <= 10:
        return f"S{11 - level}"
    if level <= 15:
        return f"G{16 - level}"
    if level <= 20:
        return f"P{21 - level}"
    if level <= 25:
        return f"D{26 - level}"
    return f"R{31 - level}"

def get_tier_group(level: Optional[int]) -> str:
    tier_name = get_tier_name(level)
    if tier_name == "Unknown":
        return "Unknown"
    return tier_name.split(" ", 1)[0]

def parse_tags(value: Any) -> List[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(parsed, list):
        return []
    return [str(tag) for tag in parsed if str(tag).strip()]

def build_empty_dashboard_stats() -> Dict[str, Any]:
    return {
        "totalSolved": 0,
        "currentStreak": 0,
        "longestStreak": 0,
        "solvedLast7Days": 0,
        "solvedLast30Days": 0,
        "averageLevel": None,
        "difficultyDistribution": [{"tier": label, "level": level, "count": 0} for level, label in DASHBOARD_LEVELS],
        "tagDistribution": [],
        "localRating": {
            "acRating": calculate_local_ac_rating({"problems": [], "classProblemGroups": []}),
            "tagRatings": [],
        },
        "recentProblems": [],
        "dailySolvedTrend": [],
    }

def calculate_streaks(solved_dates: List[date], today: date) -> Tuple[int, int]:
    unique_dates = sorted(set(solved_dates))
    if not unique_dates:
        return 0, 0

    longest = 1
    running = 1
    for previous, current in zip(unique_dates, unique_dates[1:]):
        if current == previous + timedelta(days=1):
            running += 1
        else:
            longest = max(longest, running)
            running = 1
    longest = max(longest, running)

    if today not in unique_dates:
        return 0, longest

    current_streak = 1
    cursor = today - timedelta(days=1)
    date_set = set(unique_dates)
    while cursor in date_set:
        current_streak += 1
        cursor -= timedelta(days=1)
    return current_streak, longest

def get_local_dashboard_stats(conn: sqlite3.Connection, class_problem_groups: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    stats = build_empty_dashboard_stats()
    today = date.today()
    cursor = conn.execute("""
        SELECT l.problem_id, l.logged_at, p.title, p.tier, p.tags
        FROM user_solve_log l
        LEFT JOIN problems p ON p.problem_id = l.problem_id
        WHERE l.status = 'solved'
        ORDER BY l.logged_at DESC, l.problem_id DESC
    """)
    rows = cursor.fetchall()
    if not rows:
        return stats

    solved_dates: List[date] = []
    levels: List[int] = []
    difficulty_counts = Counter({label: 0 for _, label in DASHBOARD_LEVELS})
    tag_counts: Counter[str] = Counter()
    day_counts: Counter[str] = Counter()
    recent_problems = []
    rating_problems = []

    for row in rows:
        problem_id = row["problem_id"]
        level = row["tier"] if isinstance(row["tier"], int) else None
        title = row["title"] or "제목 없음"
        solved_at = row["logged_at"] or ""
        solved_date = parse_logged_date(solved_at)
        tags = parse_tags(row["tags"])

        if solved_date:
            solved_dates.append(solved_date)
            day_counts[solved_date.isoformat()] += 1
        if level and level > 0:
            levels.append(level)

        difficulty_counts[get_short_tier_name(level)] += 1
        for tag in tags or ["태그 없음"]:
            tag_counts[tag] += 1

        rating_problems.append({
            "problemId": problem_id,
            "title": title,
            "level": level,
            "tierName": get_tier_name(level),
            "tags": tags,
            "solvedAt": solved_at,
            "isSolved": True,
            "isExtra": False,
            "isUnrated": not (isinstance(level, int) and 1 <= level <= 30),
        })

        if len(recent_problems) < 10:
            recent_problems.append({
                "problemId": problem_id,
                "title": title,
                "level": level,
                "tierName": get_tier_name(level),
                "tags": tags,
                "solvedAt": solved_at,
                "source": "sqlite",
                "bojUrl": f"https://www.acmicpc.net/problem/{problem_id}",
                "solvedAcUrl": f"https://solved.ac/search?query={problem_id}",
            })

    current_streak, longest_streak = calculate_streaks(solved_dates, today)
    stats["totalSolved"] = len(rows)
    stats["currentStreak"] = current_streak
    stats["longestStreak"] = longest_streak
    stats["solvedLast7Days"] = sum(1 for solved_date in solved_dates if solved_date >= today - timedelta(days=6))
    stats["solvedLast30Days"] = sum(1 for solved_date in solved_dates if solved_date >= today - timedelta(days=29))
    stats["averageLevel"] = round(sum(levels) / len(levels), 1) if levels else None
    stats["difficultyDistribution"] = [
        {"tier": label, "level": level, "count": difficulty_counts[label]}
        for level, label in DASHBOARD_LEVELS
    ]
    top_tags = tag_counts.most_common(10)
    stats["tagDistribution"] = [
        {
            "tag": tag,
            "count": count,
            "percent": round((count / len(rows)) * 100, 1) if rows else 0,
        }
        for tag, count in top_tags
    ]
    stats["localRating"] = {
        "acRating": calculate_local_ac_rating({
            "problems": rating_problems,
            "classProblemGroups": class_problem_groups or [],
            "contributionCount": 0,
        }),
        "tagRatings": calculate_tag_ratings(rating_problems)[:10],
    }
    stats["recentProblems"] = recent_problems
    stats["dailySolvedTrend"] = [
        {
            "date": (today - timedelta(days=offset)).isoformat(),
            "count": day_counts[(today - timedelta(days=offset)).isoformat()],
        }
        for offset in range(29, -1, -1)
    ]
    return stats

def ensure_profile_snapshot_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS solved_ac_profile_snapshots (
            handle TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            fetched_at TEXT NOT NULL
        )
    """)

def normalize_profile_snapshot(handle: str, payload: Dict[str, Any], fetched_at: str, source: str) -> Dict[str, Any]:
    return {
        "handle": payload.get("handle") or handle,
        "tier": payload.get("tier"),
        "rating": payload.get("rating"),
        "class": payload.get("class"),
        "solvedCount": payload.get("solvedCount"),
        "rank": payload.get("rank"),
        "fetchedAt": fetched_at,
        "source": source,
    }

def get_cached_profile_snapshot(conn: sqlite3.Connection, handle: str) -> Optional[Dict[str, Any]]:
    ensure_profile_snapshot_table(conn)
    cursor = conn.execute(
        "SELECT payload, fetched_at FROM solved_ac_profile_snapshots WHERE handle = ?",
        (handle,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    try:
        payload = json.loads(row["payload"])
    except (TypeError, json.JSONDecodeError):
        return None
    return normalize_profile_snapshot(handle, payload, row["fetched_at"], "sqlite_cache")

def save_profile_snapshot(conn: sqlite3.Connection, handle: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    ensure_profile_snapshot_table(conn)
    fetched_at = datetime.now().isoformat(timespec="seconds")
    conn.execute("""
        INSERT INTO solved_ac_profile_snapshots (handle, payload, fetched_at)
        VALUES (?, ?, ?)
        ON CONFLICT(handle) DO UPDATE SET
            payload = excluded.payload,
            fetched_at = excluded.fetched_at
    """, (handle, json.dumps(payload, ensure_ascii=False), fetched_at))
    conn.commit()
    return normalize_profile_snapshot(handle, payload, fetched_at, "solved_ac_api")

def get_profile_from_user_stats(conn: sqlite3.Connection, handle: str) -> Optional[Dict[str, Any]]:
    cursor = conn.execute(
        "SELECT tier, rating, solved_count, updated_at FROM user_stats ORDER BY date DESC LIMIT 1"
    )
    row = cursor.fetchone()
    if not row:
        return None
    return {
        "handle": handle,
        "tier": row["tier"],
        "rating": row["rating"],
        "class": None,
        "solvedCount": row["solved_count"],
        "rank": None,
        "fetchedAt": row["updated_at"],
        "source": "user_stats_fallback",
    }

# ----------------------------------------------------
# 📌 2. API 엔드포인트 구현
# ----------------------------------------------------

@app.get("/")
def read_root():
    return {"status": "ok", "message": "AI Tutor API Server is running."}

@app.post("/api/chat/stream")
async def chat_with_ai_stream(req: ChatRequest):
    """Gemini의 응답을 실시간으로 프론트엔드에 스트리밍합니다."""
    print(f"📥 [User Message]: {req.message} (History: {len(req.history)} items)")
    
    # 1. 사용자 메시지 DB 저장
    db.save_chat_message("user", req.message)
    
    # 2. history를 dict list로 변환하여 전달
    history_dict = [{"role": msg.role, "text": msg.text} for msg in req.history]
    
    async def wrapped_stream():
        full_response = ""
        # stream_chat_response가 동기 제너레이터라면 아래와 같이 사용
        for chunk in stream_chat_response(req.message, history_dict, req.current_problem_id):
            full_response += chunk
            yield chunk
        
        # 3. AI 응답 완료 후 DB 저장
        if full_response:
            db.save_chat_message("ai", full_response)

    return StreamingResponse(wrapped_stream(), media_type="text/plain")

@app.get("/api/chat/history")
async def get_chat_history():
    """DB에서 이전 대화 내역을 가져옵니다."""
    return {"status": "success", "history": db.get_chat_history(limit=50)}

@app.delete("/api/chat/history")
async def clear_chat_history():
    """대화 내역을 초기화합니다."""
    db.clear_chat_history()
    return {"status": "success", "message": "History cleared"}

@app.get("/api/problem/{problem_id}")
async def get_problem(problem_id: int):
    """DB에서 문제 상세 정보를 가져오는 API"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT pd.description, pd.input_desc, pd.output_desc, pd.sample_inputs, pd.sample_outputs, pd.problem_limit,
                   p.title, p.tier, p.tags
            FROM problem_details pd
            JOIN problems p ON pd.problem_id = p.problem_id
            WHERE pd.problem_id = ?
        """, (problem_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            tags_list = []
            if row[8]:
                try:
                    tags_list = json.loads(row[8])
                except json.JSONDecodeError:
                    pass

            # Check if the problem is solved
            solved_ids = db.get_solved_problem_ids()
            is_solved = problem_id in solved_ids

            return {
                "status": "success",
                "data": {
                    "description": row[0],
                    "input_desc": row[1],
                    "output_desc": row[2],
                    "sample_inputs": json.loads(row[3]) if row[3] else [],
                    "sample_outputs": json.loads(row[4]) if row[4] else [],
                    "problem_limit": row[5] or "",
                    "title": row[6] or "",
                    "tier": row[7] or 0,
                    "tags": tags_list,
                    "is_solved": is_solved
                }
            }
        else:
            raise HTTPException(status_code=404, detail="DB에 해당 문제가 없습니다.")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/judge")
async def run_judge(req: JudgeRequest):
    """사용자의 파이썬 코드를 기본/분석 모드로 검증하는 API"""
    try:
        return judge_aggregator.run(req.problem_id, req.code, req.mode).model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/judge/hint")
async def generate_judge_hint(req: HintRequestModel):
    """분석 모드 반례에 대해 사용자가 선택한 단계의 코칭 힌트를 생성합니다."""
    try:
        problem = judge_aggregator.load_problem(req.problem_id)
        hint = hint_generator.generate(problem, req.code, req.failed_case, req.hint_level)
        return HintResponseModel(hint_level=req.hint_level, hint=hint).model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"힌트 생성에 실패했습니다: {e}")

@app.get("/api/dashboard")
async def get_dashboard(handle: str = DEFAULT_SOLVED_AC_HANDLE):
    """sqlite 풀이 기록과 캐시된 solved.ac 프로필로 대시보드 데이터를 반환합니다."""
    warnings: List[str] = []
    profile = None
    stats = build_empty_dashboard_stats()

    if not os.path.exists(DB_PATH):
        warnings.append("로컬 풀이 DB를 찾지 못해 빈 대시보드를 표시합니다.")
        return {
            "status": "success",
            "handle": handle,
            "profile": profile,
            "stats": stats,
            "warnings": warnings,
        }

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        ensure_profile_snapshot_table(conn)
        class_problem_groups = get_or_fetch_class_problem_groups()
        stats = get_local_dashboard_stats(conn, class_problem_groups)
        if stats["localRating"]["acRating"].get("classStatus") == "CLASS 데이터 미연동":
            warnings.append("CLASS 문제 캐시가 없어 Local CLASS 보너스를 0점으로 계산했습니다.")

        profile = get_cached_profile_snapshot(conn, handle)
        if not profile:
            try:
                solved_ac_payload = SolvedAcClient(handle).get_user_info()
                profile = save_profile_snapshot(conn, handle, solved_ac_payload)
            except Exception as error:
                print(f"solved.ac 프로필 조회 실패: {error}")
                warnings.append("solved.ac 프로필 정보를 불러오지 못했습니다. 로컬 풀이 기록만 표시합니다.")
                profile = get_profile_from_user_stats(conn, handle)

        if stats["totalSolved"] == 0:
            warnings.append("아직 로컬 풀이 기록이 없어 통계 카드와 차트를 비워 표시합니다.")
    except sqlite3.Error as error:
        print(f"대시보드 DB 조회 실패: {error}")
        warnings.append("로컬 풀이 DB를 읽는 중 문제가 발생했습니다.")
    except Exception as error:
        print(f"대시보드 데이터 생성 실패: {error}")
        warnings.append("대시보드 데이터를 생성하는 중 문제가 발생했습니다.")
    finally:
        if conn:
            conn.close()

    return {
        "status": "success",
        "handle": handle,
        "profile": profile,
        "stats": stats,
        "warnings": warnings,
    }
    
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
    ensure_profile_snapshot_table(conn)
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
