from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

from bs4 import BeautifulSoup
from curl_cffi import requests

BASE_URL = "https://solved.ac"
DEFAULT_CLASS_LEVELS = list(range(1, 11))


def get_default_cache_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "classProblems.json"


def load_class_problem_groups(cache_path: str | Path | None = None) -> List[Dict[str, Any]]:
    path = Path(cache_path) if cache_path else get_default_cache_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(data, dict):
        groups = data.get("classes", [])
    else:
        groups = data
    return groups if isinstance(groups, list) else []


def save_class_problem_groups(groups: List[Dict[str, Any]], cache_path: str | Path | None = None) -> None:
    path = Path(cache_path) if cache_path else get_default_cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "fetchedAt": datetime.now().isoformat(timespec="seconds"),
        "source": "https://solved.ac/class?class={classLevel}",
        "classes": groups,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def extract_int(pattern: str, text: str, default: int = 0) -> int:
    match = re.search(pattern, text)
    if not match:
        return default
    return int(match.group(1).replace(",", ""))


def get_class_urls(class_level: int) -> List[str]:
    return [
        f"{BASE_URL}/class?class={class_level}",
        f"{BASE_URL}/class/{class_level}",
    ]


def fetch_html(url: str) -> str:
    response = requests.get(
        url,
        impersonate="chrome110",
        timeout=15,
        headers={"Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8"},
    )
    response.raise_for_status()
    return response.text


def parse_class_page(html: str, class_level: int, source_url: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)
    total_problems = extract_int(r"총\s*([\d,]+)\s*문제", text)
    essential_problems = extract_int(r"에센셜\s*([\d,]+)\s*문제", text)
    required_solved = extract_int(r"목록 중\s*([\d,]+)\s*문제 이상", text, default=16)

    problem_map: Dict[str, Dict[str, Any]] = {}
    for link in soup.find_all("a", href=True):
        href = str(link["href"])
        match = re.search(r"acmicpc\.net/problem/(\d+)|/problem/(\d+)", href)
        if not match:
            continue
        problem_id = match.group(1) or match.group(2)
        label = link.get_text(" ", strip=True)
        if not label or label == problem_id:
            continue
        if problem_id not in problem_map:
            parent_text = link.parent.get_text(" ", strip=True) if link.parent else label
            problem_map[problem_id] = {
                "problemId": int(problem_id),
                "title": label,
                "isEssential": "ESSENTIAL" in parent_text.upper(),
            }
        elif "ESSENTIAL" in label.upper():
            problem_map[problem_id]["isEssential"] = True

    problems = sorted(problem_map.values(), key=lambda item: item["problemId"])
    return {
        "classLevel": class_level,
        "requiredSolvedCount": required_solved,
        "totalProblems": total_problems or len(problems),
        "essentialProblems": essential_problems,
        "sourceUrl": source_url,
        "problems": problems,
    }


def fetch_class_problem_group(class_level: int) -> Dict[str, Any]:
    last_error: Exception | None = None
    for url in get_class_urls(class_level):
        try:
            html = fetch_html(url)
            group = parse_class_page(html, class_level, url)
            if group["problems"]:
                return group
        except Exception as error:
            last_error = error
    raise RuntimeError(f"CLASS {class_level} 문제 목록을 가져오지 못했습니다: {last_error}")


def fetch_class_problem_groups(class_levels: Iterable[int] = DEFAULT_CLASS_LEVELS) -> List[Dict[str, Any]]:
    return [fetch_class_problem_group(class_level) for class_level in class_levels]


def get_or_fetch_class_problem_groups(cache_path: str | Path | None = None) -> List[Dict[str, Any]]:
    cached = load_class_problem_groups(cache_path)
    if cached:
        return cached
    try:
        groups = fetch_class_problem_groups()
        save_class_problem_groups(groups, cache_path)
        return groups
    except Exception as error:
        print(f"CLASS 문제 캐시 생성 실패: {error}")
        return []
