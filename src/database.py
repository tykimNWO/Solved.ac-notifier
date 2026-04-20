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