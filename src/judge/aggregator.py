from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from src.database import DatabaseManager

from .analysis import AnalysisJudgeRunner
from .basic import BasicJudgeRunner
from .cache import ReferenceSolutionCache
from .comparator import OutputComparator
from .gemini_tests import GeminiTestCaseGenerator
from .reference_provider import ReferenceSolutionProvider
from .runner import PythonCodeRunner
from .safety import ReferenceSolutionSafetyChecker
from .types import JudgeMode, JudgeResponseModel, ProblemContext


class JudgeResultAggregator:
    def __init__(self, db_path: str | Path, data_dir: str | Path, db_manager: DatabaseManager):
        self.db_path = str(db_path)
        self.db_manager = db_manager
        self.runner = PythonCodeRunner()
        self.comparator = OutputComparator()
        self.safety_checker = ReferenceSolutionSafetyChecker()
        self.basic_runner = BasicJudgeRunner(self.runner, self.comparator, self.safety_checker)
        self.reference_provider = ReferenceSolutionProvider(
            cache=ReferenceSolutionCache(data_dir),
            runner=self.runner,
            comparator=self.comparator,
            safety_checker=self.safety_checker,
        )
        self.analysis_runner = AnalysisJudgeRunner(
            basic_runner=self.basic_runner,
            reference_provider=self.reference_provider,
            test_case_generator=GeminiTestCaseGenerator(),
            runner=self.runner,
            comparator=self.comparator,
        )

    def run(self, problem_id: int, code: str, mode: JudgeMode = "basic") -> JudgeResponseModel:
        problem = self.load_problem(problem_id)
        if mode == "analysis":
            result = self.analysis_runner.run(problem, code)
        else:
            result = self.basic_runner.run(problem, code)

        if result.verdict in {"Basic Passed", "Analysis Passed"}:
            self.db_manager.upsert_user_solve_log(problem_id, "solved")
            result.is_solved = True
        return result

    def load_problem(self, problem_id: int) -> ProblemContext:
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                """
                SELECT pd.description, pd.input_desc, pd.output_desc, pd.sample_inputs, pd.sample_outputs,
                       pd.problem_limit, p.title, p.tier, p.tags
                FROM problem_details pd
                LEFT JOIN problems p ON pd.problem_id = p.problem_id
                WHERE pd.problem_id = ?
                """,
                (problem_id,),
            )
            row = cursor.fetchone()
        finally:
            conn.close()

        if not row:
            raise ValueError("채점 데이터를 찾을 수 없습니다.")

        tags = self._json_list(row[8])
        return ProblemContext(
            problem_id=problem_id,
            description=row[0] or "",
            input_desc=row[1] or "",
            output_desc=row[2] or "",
            sample_inputs=self._json_list(row[3]),
            sample_outputs=self._json_list(row[4]),
            problem_limit=row[5] or "",
            title=row[6] or "",
            tier=row[7] or 0,
            tags=tags,
        )

    def _json_list(self, value: Any) -> list[str]:
        if not value:
            return []
        try:
            parsed = json.loads(value) if isinstance(value, str) else value
        except (TypeError, json.JSONDecodeError):
            return []
        if not isinstance(parsed, list):
            return []
        return [str(item) for item in parsed]
