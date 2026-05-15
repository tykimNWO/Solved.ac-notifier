from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Tuple

from src.services.rating.class_rating import (
    calculate_class_bonus,
    calculate_local_class_level,
    normalize_problem_id,
)


def calculate_solved_count_bonus(solved_count: int) -> int:
    return min(200, round(200 * (1 - (0.997 ** max(solved_count, 0)))))


def calculate_contribution_bonus(contribution_count: int | None = None) -> int:
    count = max(contribution_count or 0, 0)
    return round(25 * (1 - (0.9 ** count)))


def is_rating_problem(problem: Dict[str, Any]) -> bool:
    problem_id = problem.get("problemId")
    level = problem.get("level")
    if problem_id is None or normalize_problem_id(problem_id) == "":
        return False
    if problem.get("isSolved") is False:
        return False
    if problem.get("isExtra"):
        return False
    if problem.get("isUnrated"):
        return False
    return isinstance(level, int) and 1 <= level <= 30


def dedupe_rating_problems(problems: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_id: Dict[str, Dict[str, Any]] = {}
    for problem in problems:
        if not is_rating_problem(problem):
            continue
        key = normalize_problem_id(problem["problemId"])
        current = by_id.get(key)
        if current is None:
            by_id[key] = problem
            continue
        current_solved_at = str(current.get("solvedAt") or "")
        next_solved_at = str(problem.get("solvedAt") or "")
        current_metadata_score = int(bool(current.get("title"))) + int(bool(current.get("tags")))
        next_metadata_score = int(bool(problem.get("title"))) + int(bool(problem.get("tags")))
        if next_solved_at > current_solved_at or (
            next_solved_at == current_solved_at and next_metadata_score > current_metadata_score
        ):
            by_id[key] = problem
    return list(by_id.values())


def calculate_top_problem_score(
    problems: Iterable[Dict[str, Any]],
    limit: int = 100,
) -> Dict[str, Any]:
    sorted_problems = sorted(
        dedupe_rating_problems(problems),
        key=lambda problem: (problem["level"], str(problem.get("solvedAt") or ""), str(problem["problemId"])),
        reverse=True,
    )
    top_problems = sorted_problems[:limit]
    return {
        "score": sum(problem["level"] for problem in top_problems),
        "topProblems": top_problems,
    }


def calculate_local_ac_rating(input_data: Dict[str, Any]) -> Dict[str, Any]:
    problems = dedupe_rating_problems(input_data.get("problems") or [])
    class_problem_groups = input_data.get("classProblemGroups") or []
    contribution_count = input_data.get("contributionCount") or 0
    top_result = calculate_top_problem_score(problems, limit=100)
    solved_ids = {normalize_problem_id(problem["problemId"]) for problem in problems}
    class_result = calculate_local_class_level(solved_ids, class_problem_groups)

    class_level = int(class_result["classLevel"])
    top_problem_score = int(top_result["score"])
    class_bonus = calculate_class_bonus(class_level)
    solved_count_bonus = calculate_solved_count_bonus(len(problems))
    contribution_bonus = calculate_contribution_bonus(contribution_count)

    return {
        "topProblemScore": top_problem_score,
        "classBonus": class_bonus,
        "solvedCountBonus": solved_count_bonus,
        "contributionBonus": contribution_bonus,
        "total": top_problem_score + class_bonus + solved_count_bonus + contribution_bonus,
        "solvedCountForRating": len(problems),
        "topProblems": top_result["topProblems"],
        "localClassLevel": class_level,
        "classStatus": class_result["status"],
        "classProgress": class_result["classProgress"],
    }


def calculate_tag_ratings(problems: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for problem in dedupe_rating_problems(problems):
        tags = problem.get("tags") or []
        for tag in tags:
            if str(tag).strip():
                grouped[str(tag)].append(problem)

    ratings = []
    for tag, tag_problems in grouped.items():
        top_result = calculate_top_problem_score(tag_problems, limit=50)
        top_problem_score = int(top_result["score"]) * 2
        solved_count = len(tag_problems)
        solved_count_bonus = round(200 * (1 - (0.99 ** solved_count)))
        ratings.append({
            "tag": tag,
            "rating": top_problem_score + solved_count_bonus,
            "topProblemScore": top_problem_score,
            "solvedCountBonus": solved_count_bonus,
            "solvedCount": solved_count,
            "topProblems": top_result["topProblems"],
        })

    return sorted(ratings, key=lambda item: (item["rating"], item["solvedCount"], item["tag"]), reverse=True)


def run_self_check() -> Tuple[bool, List[str]]:
    sample_problems = [
        {"problemId": 1, "level": 1, "tags": ["implementation"], "isSolved": True},
        {"problemId": 2, "level": 10, "tags": ["dp"], "isSolved": True},
        {"problemId": 3, "level": 20, "tags": ["dp", "graphs"], "isSolved": True},
        {"problemId": 3, "level": 5, "tags": ["dp"], "isSolved": True},
        {"problemId": 4, "level": 0, "tags": ["unrated"], "isSolved": True},
        {"problemId": 5, "level": 30, "tags": ["extra"], "isSolved": True, "isExtra": True},
    ]
    errors: List[str] = []
    top_result = calculate_top_problem_score(sample_problems)
    if top_result["score"] != 31:
        errors.append(f"expected top score 31, got {top_result['score']}")
    if calculate_solved_count_bonus(0) != 0:
        errors.append("solved count bonus for zero should be 0")
    tag_ratings = calculate_tag_ratings(sample_problems)
    dp_rating = next((item for item in tag_ratings if item["tag"] == "dp"), None)
    if not dp_rating or dp_rating["topProblemScore"] != 60 or dp_rating["solvedCount"] != 2:
        errors.append("dp tag rating did not use top two rated dp problems")
    ac_rating = calculate_local_ac_rating({"problems": sample_problems, "classProblemGroups": []})
    if ac_rating["classBonus"] != 0 or ac_rating["classStatus"] != "CLASS 데이터 미연동":
        errors.append("empty class data should return disconnected status and zero bonus")
    return len(errors) == 0, errors


if __name__ == "__main__":
    ok, failures = run_self_check()
    if not ok:
        raise SystemExit("\n".join(failures))
    print("rating formula self-check passed")
