import time
import json
import sqlite3
from bs4 import BeautifulSoup
from curl_cffi import requests

DB_PATH = "./data/tracker.db"
BOJ_URL = "https://www.acmicpc.net/problem/"

def fetch_problem_html(problem_id):
    """curl_cffi를 사용하여 봇 차단을 우회하고 HTML을 가져옵니다."""
    url = f"{BOJ_URL}{problem_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    try:
        # impersonate="chrome110"으로 일반 크롬 브라우저인 것처럼 위장
        response = requests.get(url, headers=headers, impersonate="chrome110", timeout=10)
        if response.status_code == 200:
            return response.text
        elif response.status_code == 404:
            return "NOT_FOUND" # 없는 문제 번호
        else:
            return None
    except Exception as e:
        print(f"[{problem_id}] Network Error: {e}")
        return None

def parse_boj_html(html_text):
    """HTML에서 문제 본문, 입출력 설명, 예제 데이터를 파싱합니다."""
    soup = BeautifulSoup(html_text, 'html.parser')
    
    # 1. 본문, 입력, 출력 설명 (HTML 태그를 그대로 유지하여 나중에 React에서 렌더링하기 좋게 만듦)
    description = str(soup.select_one('#problem_description')) if soup.select_one('#problem_description') else ""
    input_desc = str(soup.select_one('#problem_input')) if soup.select_one('#problem_input') else ""
    output_desc = str(soup.select_one('#problem_output')) if soup.select_one('#problem_output') else ""
    
    # 2. 예제 입출력 추출 (여러 개인 경우가 많으므로 리스트로 수집)
    sample_inputs = []
    sample_outputs = []
    
    sample_idx = 1
    while True:
        in_elem = soup.select_one(f'#sample-input-{sample_idx}')
        out_elem = soup.select_one(f'#sample-output-{sample_idx}')
        
        if not in_elem and not out_elem:
            break
            
        if in_elem:
            sample_inputs.append(in_elem.text.strip())
        if out_elem:
            sample_outputs.append(out_elem.text.strip())
            
        sample_idx += 1

    return {
        "description": description,
        "input_desc": input_desc,
        "output_desc": output_desc,
        "sample_inputs": json.dumps(sample_inputs, ensure_ascii=False), # 배열을 JSON 문자열로 저장
        "sample_outputs": json.dumps(sample_outputs, ensure_ascii=False)
    }

def run_scraper(start_id, end_id):
    """지정된 범위의 문제를 수집하여 DB에 적재합니다."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print(f"🚀 백준 문제 수집을 시작합니다. ({start_id} ~ {end_id})")
    
    for pid in range(start_id, end_id + 1):
        # 이미 수집된 문제인지 확인 (DB 정합성 및 재시작 방어 로직)
        cursor.execute("SELECT is_scraped FROM problem_details WHERE problem_id = ?", (pid,))
        row = cursor.fetchone()
        
        if row and row[0] == 1:
            print(f"[{pid}] 이미 수집됨. 패스.")
            continue
            
        print(f"[{pid}] 수집 중...", end=" ")
        html = fetch_problem_html(pid)
        
        if html == "NOT_FOUND":
            print("❌ 없는 문제 (404)")
            # 없는 문제도 상태를 2(에러/없음)로 기록해 두어야 다음 배치 때 다시 시도하지 않음
            cursor.execute("""
                INSERT OR REPLACE INTO problem_details (problem_id, is_scraped) 
                VALUES (?, 2)
            """, (pid,))
            conn.commit()
            
        elif html:
            data = parse_boj_html(html)
            cursor.execute("""
                INSERT OR REPLACE INTO problem_details 
                (problem_id, description, input_desc, output_desc, sample_inputs, sample_outputs, is_scraped)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (
                pid, 
                data['description'], 
                data['input_desc'], 
                data['output_desc'], 
                data['sample_inputs'], 
                data['sample_outputs']
            ))
            conn.commit()
            print("✅ 완료")
        else:
            print("⚠️ 차단 또는 오류 발생")
            
        # [매우 중요] 서버에 무리를 주지 않고 차단(IP Block)을 피하기 위한 딜레이
        time.sleep(1.5)

    conn.close()
    print("🎉 수집 작업이 종료되었습니다.")

if __name__ == "__main__":
    # 테스트용: 가장 유명한 1000번(A+B)부터 1005번(ACM Craft)까지 먼저 긁어봅니다.
    run_scraper(10200, 35000)