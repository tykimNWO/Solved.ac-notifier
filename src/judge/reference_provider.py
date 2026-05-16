from __future__ import annotations

from dataclasses import dataclass, field

from .basic import run_sample_cases
from .cache import ReferenceSolutionCache
from .comparator import OutputComparator
from .gemini_reference import GeminiReferenceParseError, GeminiReferenceSolutionGenerator
from .runner import PythonCodeRunner
from .safety import ReferenceSolutionSafetyChecker
from .types import ProblemContext, ReferenceMeta, ReferenceSolution
from .utils import now_kst_iso


@dataclass
class ReferenceProviderResult:
    solution: ReferenceSolution | None
    status: str
    warnings: list[str] = field(default_factory=list)
    error: str = ""


class ReferenceSolutionProvider:
    def __init__(
        self,
        cache: ReferenceSolutionCache,
        generator: GeminiReferenceSolutionGenerator | None = None,
        runner: PythonCodeRunner | None = None,
        comparator: OutputComparator | None = None,
        safety_checker: ReferenceSolutionSafetyChecker | None = None,
    ):
        self.cache = cache
        self.generator = generator or GeminiReferenceSolutionGenerator()
        self.runner = runner or PythonCodeRunner()
        self.comparator = comparator or OutputComparator()
        self.safety_checker = safety_checker or ReferenceSolutionSafetyChecker()

    def get(self, problem: ProblemContext) -> ReferenceProviderResult:
        cached, cache_warnings = self.cache.load(problem.problem_id)
        if cached:
            safety = self.safety_checker.check(cached.code, strict_imports=True)
            warnings = cache_warnings + cached.meta.warnings + safety.warnings
            if safety.ok:
                return ReferenceProviderResult(cached, "ok", warnings=warnings)
            return ReferenceProviderResult(
                None,
                "error",
                warnings=warnings,
                error="캐시된 reference solution에서 위험 코드가 감지되었습니다.",
            )

        try:
            generated = self.generator.generate(problem)
        except GeminiReferenceParseError as error:
            debug = error.debug
            print(
                f"[{now_kst_iso()}] [JUDGE_REFERENCE_GENERATION_FAILED] "
                f"problem_id={problem.problem_id} "
                f"finish_reason={debug.get('finish_reason')} "
                f"finish_message={debug.get('finish_message')} "
                f"response_length={debug.get('response_length')} "
                f"response_preview={debug.get('response_preview')} "
                f"error={error}"
            )
            return ReferenceProviderResult(
                None,
                "unavailable",
                warnings=cache_warnings,
                error=f"Gemini reference solution 응답이 불완전해 파싱하지 못했습니다: {error}",
            )
        except Exception as error:
            print(f"[{now_kst_iso()}] [JUDGE_REFERENCE_GENERATION_FAILED] problem_id={problem.problem_id} error={error}")
            return ReferenceProviderResult(
                None,
                "unavailable",
                warnings=cache_warnings,
                error=f"Gemini reference solution 생성에 실패했습니다: {error}",
            )

        code = (generated.get("solution_code") or "").strip()
        if not code:
            return ReferenceProviderResult(
                None,
                "unavailable",
                warnings=cache_warnings + ["Gemini가 reference solution 코드를 반환하지 않았습니다."],
            )

        safety = self.safety_checker.check(code, strict_imports=True)
        if not safety.ok:
            return ReferenceProviderResult(
                None,
                "error",
                warnings=cache_warnings + safety.warnings,
                error="생성된 reference solution 안전성 검사에 실패했습니다: " + "; ".join(safety.errors),
            )

        sample_results = run_sample_cases(problem, code, self.runner, self.comparator)
        sample_passed = bool(sample_results) and all(result.result == "Success" for result in sample_results)
        if not sample_passed:
            first_error = next((result.result for result in sample_results if result.result != "Success"), "unknown")
            return ReferenceProviderResult(
                None,
                "error",
                warnings=cache_warnings + safety.warnings,
                error=f"생성된 reference solution이 공식 예제 검증에 실패했습니다: {first_error}",
            )

        now = now_kst_iso()
        confidence = generated.get("confidence") or "medium"
        if confidence not in {"high", "medium", "low"}:
            confidence = "medium"
        meta = ReferenceMeta(
            problem_id=problem.problem_id,
            created_at=now,
            updated_at=now,
            validated_samples=True,
            validation_status="sample_passed",
            confidence=confidence,
            confidence_reasons=generated.get("confidence_reasons") or [
                "Reference solution passed all official sample tests."
            ],
            warnings=(generated.get("warnings") or []) + safety.warnings,
            source_notes=generated.get("source_notes")
            or "Reference solution was generated or rewritten by Gemini based on web search results and problem statement.",
            algorithm_summary=generated.get("algorithm_summary") or "",
        )
        saved = self.cache.save(problem.problem_id, code, meta)
        return ReferenceProviderResult(saved, "ok", warnings=cache_warnings + meta.warnings)
