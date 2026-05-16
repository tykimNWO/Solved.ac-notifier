from __future__ import annotations

import os
from typing import Any

from google import genai
from google.genai import types

import config

from .types import ProblemContext, ReferenceConfidence
from .utils import extract_json_object, html_to_text


def get_judge_model_id() -> str:
    return (
        os.environ.get("JUDGE_GEMINI_MODEL_ID")
        or os.environ.get("GEMINI_MODEL_ID")
        or "gemini-3.1-flash-lite"
    )


class GeminiReferenceSolutionGenerator:
    def __init__(self, model_id: str | None = None):
        self.model_id = model_id or get_judge_model_id()
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)

    def generate(self, problem: ProblemContext) -> dict[str, Any]:
        prompt = f"""
You are building a safe Python reference solution for BOJ problem {problem.problem_id}.
Use Google Search grounding only as background context. Do not copy web code verbatim.

Return compact JSON only:
{{
  "solution_lines": ["import sys", "def main():", "    ...", "if __name__ == '__main__':", "    main()"],
  "algorithm_summary": "short Korean or English summary",
  "confidence": "high|medium|low"
}}

- Put Python code in solution_lines as an array of single-line strings.
- Do not add markdown fences or extra keys unless necessary.
- Python only. stdin/stdout only. No filesystem, network, subprocess, eval, exec, open, pickle, threading, multiprocessing, ctypes, or importlib.

Problem title: {problem.title}
Tags: {", ".join(problem.tags)}
Limit: {html_to_text(problem.problem_limit)}
Description:
{html_to_text(problem.description)[:2500]}

Input:
{html_to_text(problem.input_desc)[:1200]}

Output:
{html_to_text(problem.output_desc)[:1200]}

Samples:
{self._format_samples(problem)}
"""
        response = self.client.models.generate_content(
            model=self.model_id,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
                max_output_tokens=4096,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
        try:
            parsed = self._parse_response(response)
        except Exception as error:
            debug = self._response_debug_details(response)
            details = self._format_debug_details(debug)
            raise GeminiReferenceParseError(
                f"Gemini 응답 JSON 파싱 실패: {error}. {details}",
                debug=debug,
            ) from error
        confidence = parsed.get("confidence") or "medium"
        if confidence not in {"high", "medium", "low"}:
            confidence = "medium"
        parsed["confidence"] = confidence
        parsed["solution_code"] = self._extract_solution_code(parsed)
        parsed["algorithm_summary"] = str(parsed.get("algorithm_summary") or "")
        parsed["confidence_reasons"] = self._string_list(parsed.get("confidence_reasons"))
        parsed["warnings"] = self._string_list(parsed.get("warnings"))
        parsed["source_notes"] = str(parsed.get("source_notes") or "")
        return parsed

    def _parse_response(self, response: Any) -> dict[str, Any]:
        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, dict):
            return parsed
        if hasattr(parsed, "model_dump"):
            dumped = parsed.model_dump()
            if isinstance(dumped, dict):
                return dumped
        return extract_json_object(getattr(response, "text", "") or "")

    def _extract_solution_code(self, parsed: dict[str, Any]) -> str:
        solution_lines = parsed.get("solution_lines")
        if isinstance(solution_lines, list):
            return "\n".join(str(line) for line in solution_lines)
        return str(parsed.get("solution_code") or "")

    def _format_samples(self, problem: ProblemContext) -> str:
        chunks = []
        for index, sample_input in enumerate(problem.sample_inputs):
            expected = problem.sample_outputs[index] if index < len(problem.sample_outputs) else ""
            chunks.append(f"[Sample {index + 1} input]\n{sample_input}\n[Sample {index + 1} output]\n{expected}")
        return "\n\n".join(chunks)

    def _string_list(self, value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        if value:
            return [str(value)]
        return []

    def _response_debug_details(self, response: Any) -> dict[str, Any]:
        text = getattr(response, "text", "") or ""
        preview = text.replace("\n", "\\n")[:700]
        finish_reason = ""
        finish_message = ""
        candidates = getattr(response, "candidates", None) or []
        if candidates:
            first = candidates[0]
            finish_reason = str(getattr(first, "finish_reason", "") or "")
            finish_message = str(getattr(first, "finish_message", "") or "")
        return {
            "finish_reason": finish_reason or "unknown",
            "finish_message": finish_message or "-",
            "response_length": len(text),
            "response_preview": preview,
        }

    def _format_debug_details(self, debug: dict[str, Any]) -> str:
        return (
            f"finish_reason={debug.get('finish_reason')} "
            f"finish_message={debug.get('finish_message')} "
            f"response_length={debug.get('response_length')} "
            f"response_preview={debug.get('response_preview')}"
        )


ReferenceConfidenceValue = ReferenceConfidence


class GeminiReferenceParseError(ValueError):
    def __init__(self, message: str, debug: dict[str, Any]):
        super().__init__(message)
        self.debug = debug
