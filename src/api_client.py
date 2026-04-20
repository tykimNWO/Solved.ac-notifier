from curl_cffi import requests

class SolvedAcClient:
    BASE_URL = "https://solved.ac/api/v3"

    def __init__(self, handle):
        self.handle = handle
        self.impersonate = "chrome110"

    def get_user_info(self):
        """사용자 기본 정보 조회"""
        url = f"{self.BASE_URL}/user/show?handle={self.handle}"
        response = requests.get(url, impersonate=self.impersonate)
        response.raise_for_status()
        return response.json()

    def get_user_tag_stats(self):
        """사용자의 태그별 문제 풀이 통계 조회"""
        url = f"{self.BASE_URL}/user/problem_tag_stats?handle={self.handle}"
        response = requests.get(url, impersonate=self.impersonate)
        response.raise_for_status()
        return response.json()

    def search_problems(self, query, page=1):
        """쿼리를 기반으로 문제 메타데이터 검색 (예: tier:b5..p1)"""
        url = f"{self.BASE_URL}/search/problem"
        params = {"query": query, "page": page}
        response = requests.get(url, impersonate=self.impersonate, params=params)
        response.raise_for_status()
        return response.json()