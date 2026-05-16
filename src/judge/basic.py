from __future__ import annotations

from .comparator import OutputComparator
from .runner import PythonCodeRunner
from .safety import ReferenceSolutionSafetyChecker
from .types import CaseResult, JudgeResponseModel, ProblemContext, ReferenceStatus


class BasicJudgeRunner:
    def __init__(
        self,
        runner: PythonCodeRunner | None = None,
        comparator: OutputComparator | None = None,
        safety_checker: ReferenceSolutionSafetyChecker | None = None,
    ):
        self.runner = runner or PythonCodeRunner()
        self.comparator = comparator or OutputComparator()
        self.safety_checker = safety_checker or ReferenceSolutionSafetyChecker()

    def run(self, problem: ProblemContext, code: str) -> JudgeResponseModel:
        safety = self.safety_checker.check(code, strict_imports=False)
        warnings = list(safety.warnings)
        if not safety.ok:
            return JudgeResponseModel(
                mode="basic",
                problem_id=problem.problem_id,
                verdict="Sample Failed",
                sample_passed=False,
                reference=ReferenceStatus(available=False),
                results=[
                    CaseResult(
                        case=0,
                        name="static_safety_check",
                        input="",
                        result="Security Error",
                        error="\n".join(safety.errors),
                    )
                ],
                warnings=warnings,
                message="코드 실행 전 안전성 검사에서 위험 요소가 감지되었습니다.",
                is_solved=False,
            )

        results = run_sample_cases(problem, code, self.runner, self.comparator)
        sample_passed = bool(results) and all(result.result == "Success" for result in results)
        return JudgeResponseModel(
            mode="basic",
            problem_id=problem.problem_id,
            verdict="Basic Passed" if sample_passed else "Sample Failed",
            sample_passed=sample_passed,
            reference=ReferenceStatus(available=False),
            results=results,
            warnings=warnings,
            message=(
                "예제 입출력 기준으로 통과했습니다."
                if sample_passed
                else "예제 입출력에서 다른 결과가 확인되었습니다."
            ),
            is_solved=sample_passed,
        )


def run_sample_cases(
    problem: ProblemContext,
    code: str,
    runner: PythonCodeRunner,
    comparator: OutputComparator,
) -> list[CaseResult]:
    results: list[CaseResult] = []
    for index, sample_input in enumerate(problem.sample_inputs):
        expected = problem.sample_outputs[index] if index < len(problem.sample_outputs) else ""
        execution = runner.run(code, sample_input)
        case_number = index + 1
        if execution.timed_out:
            result = CaseResult(
                case=case_number,
                name=f"sample_{case_number}",
                input=sample_input,
                expected=expected.strip(),
                actual=(execution.stdout or "").strip(),
                result="Time Limit Exceeded",
                time=f"{execution.elapsed_ms:.1f}ms",
            )
        elif execution.exit_code != 0:
            result = CaseResult(
                case=case_number,
                name=f"sample_{case_number}",
                input=sample_input,
                expected=expected.strip(),
                actual=(execution.stdout or "").strip(),
                result="Runtime Error",
                time=f"{execution.elapsed_ms:.1f}ms",
                error=execution.stderr,
                runtime_error={"stderr": execution.stderr, "exit_code": execution.exit_code},
            )
        elif comparator.equals(execution.stdout, expected):
            result = CaseResult(
                case=case_number,
                name=f"sample_{case_number}",
                input=sample_input,
                expected=expected.strip(),
                actual=execution.stdout.strip(),
                result="Success",
                time=f"{execution.elapsed_ms:.1f}ms",
            )
        else:
            result = CaseResult(
                case=case_number,
                name=f"sample_{case_number}",
                input=sample_input,
                expected=expected.strip(),
                actual=execution.stdout.strip(),
                result="Different Output",
                time=f"{execution.elapsed_ms:.1f}ms",
            )
        results.append(result)
    return results

