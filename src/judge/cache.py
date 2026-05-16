from __future__ import annotations

import json
from pathlib import Path

from .types import ReferenceMeta, ReferenceSolution


class ReferenceSolutionCache:
    def __init__(self, data_dir: str | Path):
        self.root = Path(data_dir) / "reference_solutions"

    def problem_dir(self, problem_id: int) -> Path:
        return self.root / str(problem_id)

    def load(self, problem_id: int) -> tuple[ReferenceSolution | None, list[str]]:
        target_dir = self.problem_dir(problem_id)
        solution_path = target_dir / "solution.py"
        meta_path = target_dir / "meta.json"
        if not solution_path.exists() or not meta_path.exists():
            return None, []

        try:
            code = solution_path.read_text(encoding="utf-8")
            meta = ReferenceMeta.model_validate(json.loads(meta_path.read_text(encoding="utf-8")))
            return ReferenceSolution(code=code, meta=meta, cache_hit=True), []
        except Exception as error:
            return None, [f"손상된 reference solution 캐시를 무시했습니다: {error}"]

    def save(self, problem_id: int, code: str, meta: ReferenceMeta) -> ReferenceSolution:
        target_dir = self.problem_dir(problem_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "solution.py").write_text(code.rstrip() + "\n", encoding="utf-8")
        (target_dir / "meta.json").write_text(
            json.dumps(meta.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return ReferenceSolution(code=code, meta=meta, cache_hit=False)

