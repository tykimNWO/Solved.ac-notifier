from __future__ import annotations

from .basic import BasicJudgeRunner
from .comparator import OutputComparator
from .gemini_tests import GeminiTestCaseGenerator
from .reference_provider import ReferenceSolutionProvider
from .runner import PythonCodeRunner
from .types import (
    CaseResult,
    FirstFailedCase,
    JudgeResponseModel,
    ProblemContext,
    ReferenceStatus,
)


class AnalysisJudgeRunner:
    def __init__(
        self,
        basic_runner: BasicJudgeRunner,
        reference_provider: ReferenceSolutionProvider,
        test_case_generator: GeminiTestCaseGenerator,
        runner: PythonCodeRunner | None = None,
        comparator: OutputComparator | None = None,
    ):
        self.basic_runner = basic_runner
        self.reference_provider = reference_provider
        self.test_case_generator = test_case_generator
        self.runner = runner or PythonCodeRunner()
        self.comparator = comparator or OutputComparator()

    def run(self, problem: ProblemContext, code: str) -> JudgeResponseModel:
        basic = self.basic_runner.run(problem, code)
        sample_results = basic.results
        if basic.verdict == "Sample Failed":
            return basic.model_copy(
                update={
                    "mode": "analysis",
                    "message": "분석 모드에서도 먼저 공식 예제를 확인했고, 예제에서 다른 결과가 확인되었습니다.",
                    "is_solved": False,
                }
            )

        provider_result = self.reference_provider.get(problem)
        if not provider_result.solution:
            verdict = "Reference Error" if provider_result.status == "error" else "Reference Unavailable"
            return JudgeResponseModel(
                mode="analysis",
                problem_id=problem.problem_id,
                verdict=verdict,
                sample_passed=True,
                reference=ReferenceStatus(available=False, warnings=provider_result.warnings),
                results=sample_results,
                warnings=provider_result.warnings + ([provider_result.error] if provider_result.error else []),
                message=(
                    "reference solution을 검증하지 못해 분석 모드를 완료하지 못했습니다."
                    if verdict == "Reference Error"
                    else "reference solution을 확보하지 못해 분석 모드를 완료하지 못했습니다."
                ),
                is_solved=False,
            )

        reference = provider_result.solution
        warnings = list(provider_result.warnings)
        reference_status = ReferenceStatus(
            available=True,
            confidence=reference.meta.confidence,
            warnings=reference.meta.warnings,
            cache_hit=reference.cache_hit,
        )

        try:
            generated_cases, categories, bug_patterns = self.test_case_generator.generate(problem, code, reference)
        except Exception as error:
            warnings.append(f"추가 테스트 생성에 실패했습니다: {error}")
            return JudgeResponseModel(
                mode="analysis",
                problem_id=problem.problem_id,
                verdict="Needs Review",
                sample_passed=True,
                reference=reference_status,
                results=sample_results,
                warnings=warnings,
                message="예제는 통과했지만 추가 테스트를 생성하지 못해 사용자 검토가 필요합니다.",
                is_solved=False,
            )

        if reference.meta.confidence == "low":
            warnings.append("이 문제의 reference solution 신뢰도가 낮습니다. 분석 결과는 참고용으로만 확인해주세요.")
        if len(generated_cases) < 3:
            warnings.append("생성된 추가 테스트 수가 적어 Needs Review로 함께 표시합니다.")
        warnings.extend(bug_patterns[:3])

        analysis_results: list[CaseResult] = []
        first_failed: FirstFailedCase | None = None
        failed_count = 0

        for index, test_case in enumerate(generated_cases):
            expected_exec = self.runner.run(reference.code, test_case.input)
            if expected_exec.timed_out or expected_exec.exit_code != 0:
                return JudgeResponseModel(
                    mode="analysis",
                    problem_id=problem.problem_id,
                    verdict="Reference Error",
                    sample_passed=True,
                    generated_test_count=len(generated_cases),
                    failed_test_count=0,
                    reference=reference_status,
                    results=sample_results + analysis_results,
                    warnings=warnings + ["reference solution이 추가 테스트에서 안정적으로 실행되지 않았습니다."],
                    message="reference solution 실행 검증 중 문제가 발생했습니다.",
                    is_solved=False,
                )

            actual_exec = self.runner.run(code, test_case.input)
            expected = expected_exec.stdout
            actual = actual_exec.stdout
            result_name = "Success"
            runtime_error = None

            if actual_exec.timed_out:
                result_name = "Time Limit Exceeded"
                runtime_error = {"stderr": actual_exec.stderr, "exit_code": None, "timed_out": True}
            elif actual_exec.exit_code != 0:
                result_name = "Runtime Error"
                runtime_error = {
                    "stderr": actual_exec.stderr,
                    "exit_code": actual_exec.exit_code,
                    "timed_out": False,
                }
            elif not self.comparator.equals(actual, expected):
                result_name = "Different Output"

            case_result = CaseResult(
                case=len(sample_results) + index + 1,
                name=test_case.name,
                input=test_case.input,
                expected=expected.strip(),
                actual=actual.strip(),
                result=result_name,
                time=f"{actual_exec.elapsed_ms:.1f}ms",
                reason=test_case.reason,
                runtime_error=runtime_error,
                error=actual_exec.stderr if actual_exec.stderr else None,
            )
            analysis_results.append(case_result)

            if result_name != "Success":
                failed_count += 1
                if first_failed is None:
                    first_failed = FirstFailedCase(
                        name=test_case.name,
                        input=test_case.input,
                        expected=expected,
                        actual=actual,
                        reason=test_case.reason,
                        runtime_error=runtime_error,
                    )

        if first_failed:
            return JudgeResponseModel(
                mode="analysis",
                problem_id=problem.problem_id,
                verdict="Counterexample Found",
                sample_passed=True,
                generated_test_count=len(generated_cases),
                failed_test_count=failed_count,
                first_failed_case=first_failed,
                reference=reference_status,
                results=sample_results + analysis_results,
                warnings=warnings,
                message="예제는 통과했지만 추가 테스트에서 다른 결과가 발견되었습니다.",
                is_solved=False,
            )

        message = "분석 모드에서 생성한 추가 테스트 기준으로 통과했습니다."
        if categories:
            message += f" 확인한 유형: {', '.join(categories[:4])}."
        return JudgeResponseModel(
            mode="analysis",
            problem_id=problem.problem_id,
            verdict="Analysis Passed",
            sample_passed=True,
            generated_test_count=len(generated_cases),
            failed_test_count=0,
            reference=reference_status,
            results=sample_results + analysis_results,
            warnings=warnings,
            message=message,
            is_solved=True,
        )
