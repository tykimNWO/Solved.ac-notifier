from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


JudgeMode = Literal["basic", "analysis"]
JudgeVerdict = Literal[
    "Basic Passed",
    "Sample Failed",
    "Analysis Passed",
    "Counterexample Found",
    "Reference Unavailable",
    "Reference Error",
    "Needs Review",
]
ReferenceConfidence = Literal["high", "medium", "low"]
HintLevel = Literal["level_1", "level_2", "level_3", "level_4"]

ANALYSIS_DISCLAIMER = "분석 모드는 BOJ 공식 채점이 아니라 참고용 검증입니다."


class ProblemContext(BaseModel):
    problem_id: int
    title: str = ""
    description: str = ""
    input_desc: str = ""
    output_desc: str = ""
    problem_limit: str = ""
    sample_inputs: List[str] = Field(default_factory=list)
    sample_outputs: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    tier: int = 0


class SafetyReport(BaseModel):
    ok: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ExecutionResult(BaseModel):
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None
    elapsed_ms: float = 0.0
    timed_out: bool = False


class CaseResult(BaseModel):
    case: int
    name: str
    input: str
    expected: Optional[str] = None
    actual: Optional[str] = None
    result: str
    time: Optional[str] = None
    error: Optional[str] = None
    reason: Optional[str] = None
    runtime_error: Optional[Dict[str, Any]] = None


class ReferenceMeta(BaseModel):
    problem_id: int
    language: str = "python"
    source_type: str = "gemini_filtered_web_reference"
    created_at: str
    updated_at: str
    validated_samples: bool = False
    validation_status: str = "unknown"
    confidence: ReferenceConfidence = "medium"
    confidence_reasons: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    source_notes: str = ""
    algorithm_summary: str = ""


class ReferenceSolution(BaseModel):
    code: str
    meta: ReferenceMeta
    cache_hit: bool = False


class ReferenceStatus(BaseModel):
    available: bool = False
    confidence: Optional[ReferenceConfidence] = None
    warnings: List[str] = Field(default_factory=list)
    cache_hit: bool = False


class GeneratedTestCase(BaseModel):
    name: str
    input: str
    reason: str = ""


class FirstFailedCase(BaseModel):
    name: str
    input: str
    expected: str
    actual: str
    reason: str = ""
    runtime_error: Optional[Dict[str, Any]] = None


class JudgeResponseModel(BaseModel):
    status: str = "success"
    mode: JudgeMode
    problem_id: int
    verdict: JudgeVerdict
    sample_passed: bool
    generated_test_count: int = 0
    failed_test_count: int = 0
    first_failed_case: Optional[FirstFailedCase] = None
    reference: ReferenceStatus = Field(default_factory=ReferenceStatus)
    results: List[CaseResult] = Field(default_factory=list)
    message: str = ""
    warnings: List[str] = Field(default_factory=list)
    disclaimer: str = ANALYSIS_DISCLAIMER
    is_solved: bool = False


class HintRequestModel(BaseModel):
    problem_id: int
    code: str
    failed_case: FirstFailedCase
    hint_level: HintLevel


class HintResponseModel(BaseModel):
    status: str = "success"
    hint_level: HintLevel
    hint: str
    disclaimer: str = ANALYSIS_DISCLAIMER

