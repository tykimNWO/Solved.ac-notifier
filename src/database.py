import sqlite3
import json

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self._create_tables()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def _create_tables(self):
        with self.get_connection() as conn:
            # 1. 사용자 일별 스탯
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_stats (
                    date TEXT PRIMARY KEY,
                    tier INTEGER,
                    rating INTEGER,
                    solved_count INTEGER,
                    streak INTEGER,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # 2. 문제 메타데이터
            conn.execute("""
                CREATE TABLE IF NOT EXISTS problems (
                    problem_id INTEGER PRIMARY KEY,
                    title TEXT,
                    tier INTEGER,
                    tags TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # 2-1. 문제 상세 정보 (HTML 본문 등)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS problem_details (
                    problem_id INTEGER PRIMARY KEY,
                    description TEXT,
                    input_desc TEXT,
                    output_desc TEXT,
                    sample_inputs TEXT,
                    sample_outputs TEXT,
                    problem_limit TEXT,
                    is_scraped INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # 3. 사용자 태그별 통계
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_tag_stats (
                    date TEXT,
                    tag_id TEXT,
                    solved_count INTEGER,
                    PRIMARY KEY (date, tag_id)
                )
            """)
            # 4. 사용자 문제 풀이 이력 (추천 제외 및 로깅용)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_solve_log (
                    problem_id INTEGER PRIMARY KEY,
                    status TEXT,
                    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def upsert_user_stats(self, date, tier, rating, solved_count, streak):
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO user_stats (date, tier, rating, solved_count, streak)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    tier=excluded.tier,
                    rating=excluded.rating,
                    solved_count=excluded.solved_count,
                    streak=excluded.streak,
                    updated_at=CURRENT_TIMESTAMP
            """, (date, tier, rating, solved_count, streak))

    def upsert_problem(self, problem_id, title, tier, tags):
        # SQLite는 배열 타입이 없으므로 태그 리스트를 JSON 문자열로 변환하여 저장
        tags_str = json.dumps(tags, ensure_ascii=False)
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO problems (problem_id, title, tier, tags)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(problem_id) DO UPDATE SET
                    title=excluded.title,
                    tier=excluded.tier,
                    tags=excluded.tags,
                    updated_at=CURRENT_TIMESTAMP
            """, (problem_id, title, tier, tags_str))

    def upsert_user_tag_stats(self, date, tag_id, solved_count):
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO user_tag_stats (date, tag_id, solved_count)
                VALUES (?, ?, ?)
                ON CONFLICT(date, tag_id) DO UPDATE SET
                    solved_count=excluded.solved_count
            """, (date, tag_id, solved_count))
            
    def upsert_user_solve_log(self, problem_id, status="solved"):
        """사용자의 개별 문제 풀이 이력을 기록 (기본값: solved)"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO user_solve_log (problem_id, status)
                VALUES (?, ?)
                ON CONFLICT(problem_id) DO UPDATE SET
                    status=excluded.status,
                    logged_at=CURRENT_TIMESTAMP
            """, (problem_id, status))

    def get_solved_problem_ids(self):
        """이미 푼 문제 ID 목록을 반환합니다."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT problem_id FROM user_solve_log WHERE status='solved'")
            return [row[0] for row in cursor.fetchall()]

    def get_latest_user_stats(self):
        """가장 최근의 사용자 스탯을 반환합니다."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT tier, rating, solved_count, streak FROM user_stats ORDER BY date DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                return {
                    "tier": row[0],
                    "rating": row[1],
                    "solved_count": row[2],
                    "streak": row[3]
                }
            return None