import rumps
import multiprocessing
from src.chat_window import open_chat_window

class SolvedNotifierApp(rumps.App):
    def __init__(self):
        super(SolvedNotifierApp, self).__init__("🔥 34") # 임시 스트릭 표시
        self.menu = [
            "내 정보 확인",
            None, # 구분선(Separator)
            "🤖 AI 튜터와 대화하기 (Chat)"
        ]

    @rumps.clicked("🤖 AI 튜터와 대화하기 (Chat)")
    def open_chat(self, _):
        # 새로운 프로세스를 생성하여 WebView 실행 (Mac OS 멈춤 방지)
        p = multiprocessing.Process(target=open_chat_window)
        p.start()