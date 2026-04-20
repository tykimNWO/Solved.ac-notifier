# solved.ac notifier

React 기반 프론트엔드와 FastAPI 백엔드를 묶어서, 백준 문제 상세/예제/메모/채점 및 AI 채팅을 제공하는 프로젝트입니다.

## 아키텍처 (현재 리포 기준)

```
solved-ac-notifier/
├── main.py                  # FastAPI 백엔드 엔트리 (문제 조회/채점/메모/스트리밍 채팅)
├── config.py                # 로컬 설정 (민감정보는 환경변수로 주입)
├── data/
│   └── tracker.db           # SQLite DB (problem_details, memos 등)
├── src/
│   ├── api_client.py        # solved.ac API 클라이언트 (검색/통계 등)
│   ├── boj_scraper.py       # BOJ HTML 수집/파싱 → problem_details 적재
│   ├── database.py          # solved.ac 데이터 저장용 SQLite CRUD
│   ├── menu_app.py          # (실험/초기) 메뉴바 앱 로직
│   └── recommender.py       # 채팅 스트리밍/추천 로직 (백엔드에서 사용)
├── vectorDB.py              # (실험/초기) 벡터DB/RAG 관련 코드
├── frontend/                # React(Vite) 프론트엔드
│   ├── src/App.tsx          # UI 메인 (문제 조회 시 problem_limit 렌더링 포함)
│   └── ...
├── backup/                  # 백업 파일 (커밋 제외)
└── test/                    # 테스트/일회성 스크립트 (커밋 제외)
```

## 환경변수

- **`USER_HANDLE`**: solved.ac 핸들
- **`GEMINI_API_KEY`**: Gemini API Key (로컬에서만 설정)