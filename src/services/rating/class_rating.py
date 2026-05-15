from __future__ import annotations

from typing import Any, Dict, Iterable, List, Set, Tuple

CLASS_BONUS_TABLE = {
    0: 0,
    1: 25,
    2: 50,
    3: 100,
    4: 150,
    5: 200,
    6: 210,
    7: 220,
    8: 230,
    9: 240,
    10: 250,
}


def normalize_problem_id(problem_id: Any) -> str:
    return str(problem_id).strip()


def calculate_class_bonus(class_level: int) -> int:
    return CLASS_BONUS_TABLE.get(class_level, 0)


def calculate_local_class_level(
    solved_problem_ids: Set[str],
    class_problem_groups: Iterable[Dict[str, Any]] | None,
) -> Dict[str, Any]:
    groups = list(class_problem_groups or [])
    if not groups:
        return {
            "classLevel": 0,
            "status": "CLASS 데이터 미연동",
            "classProgress": [],
        }

    highest_class = 0
    progress: List[Dict[str, Any]] = []
    for group in sorted(groups, key=lambda item: item.get("classLevel", 0)):
        class_level = int(group.get("classLevel") or 0)
        required = int(group.get("requiredSolvedCount") or 0)
        problems = group.get("problems") or []
        class_problem_ids = {
            normalize_problem_id(problem.get("problemId"))
            for problem in problems
            if problem.get("problemId") is not None
        }
        solved_count = len(class_problem_ids & solved_problem_ids)
        achieved = required > 0 and solved_count >= required
        if achieved:
            highest_class = max(highest_class, class_level)
        progress.append({
            "classLevel": class_level,
            "requiredSolvedCount": required,
            "solvedCount": solved_count,
            "totalProblems": int(group.get("totalProblems") or len(class_problem_ids)),
            "essentialProblems": int(group.get("essentialProblems") or 0),
            "achieved": achieved,
        })

    status = f"Local CLASS {highest_class}" if highest_class else "취득한 Local CLASS 없음"
    return {
        "classLevel": highest_class,
        "status": status,
        "classProgress": progress,
    }
