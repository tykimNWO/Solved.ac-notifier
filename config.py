import os

# 디렉토리 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "tracker.db")

# 사용자 정보
USER_HANDLE = os.environ.get("USER_HANDLE", "your-handle")

# 향후 Gemini 연동 시 사용할 키 (환경변수에서 불러오는 것을 권장)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")