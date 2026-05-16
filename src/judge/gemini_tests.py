from __future__ import annotations

from typing import Any

from google import genai
from google.genai import types

import config

from .gemini_reference import get_judge_model_id
from .types import GeneratedTestCase, ProblemContext, ReferenceSolution
from .utils import extract_json_object, html_to_text


class GeminiTestCaseGenerator:
    def __init__(self, model_id: str | None = None, max_cases: int = 12):
        self.model_id = model_id or get_judge_model_id()
        self.max_cases = max_cases
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)

    def generate(self, problem: ProblemContext, user_code: str, reference: ReferenceSolution) -> tuple[list[GeneratedTestCase], list[str], list[str]]:
        prompt = f"""
Generate additional BOJ test inputs for analysis mode.
Gemini is not the judge. Do not produce expected outputs.
Return JSON only:
{{
  "edge_case_categories": ["category"],
  "generated_test_cases": [
    {{"name": "minimum_case", "input_lines": ["1"], "reason": "why this input matters"}}
  ],
  "suspected_complexity_risk": "none|low|medium|high",
  "possible_bug_patterns": ["pattern"]
}}

Important JSON formatting rules:
- Put each test input in input_lines as an array of lines without trailing newline characters.
- Do not put raw multiline input inside one JSON string.
- Do not include expected output. The server will run the reference solution.

Problem ID: {problem.problem_id}
Title: {problem.title}
Tags: {", ".join(problem.tags)}
Limit: {html_to_text(problem.problem_limit)}
Description:
{html_to_text(problem.description)[:5000]}

Input:
{html_to_text(problem.input_desc)[:2000]}

Output:
{html_to_text(problem.output_desc)[:2000]}

Official samples:
{self._format_samples(problem)}

Reference algorithm summary:
{reference.meta.algorithm_summary}

User code:
```python
{user_code[:7000]}
```
"""
        response = self.client.models.generate_content(
            model=self.model_id,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.35),
        )
        parsed = extract_json_object(response.text or "")
        raw_cases = parsed.get("generated_test_cases") or []
        cases = []
        if isinstance(raw_cases, list):
            for index, item in enumerate(raw_cases[: self.max_cases]):
                if not isinstance(item, dict):
                    continue
                input_text = self._input_text(item)
                if not input_text:
                    continue
                cases.append(
                    GeneratedTestCase(
                        name=str(item.get("name") or f"generated_{index + 1}"),
                        input=input_text,
                        reason=str(item.get("reason") or ""),
                    )
                )
        categories = self._string_list(parsed.get("edge_case_categories"))
        bug_patterns = self._string_list(parsed.get("possible_bug_patterns"))
        risk = parsed.get("suspected_complexity_risk")
        if risk and risk != "none":
            bug_patterns.append(f"복잡도 위험 신호: {risk}")
        return cases, categories, bug_patterns

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

    def _input_text(self, item: dict[str, Any]) -> str:
        input_lines = item.get("input_lines")
        if isinstance(input_lines, list):
            return "\n".join(str(line) for line in input_lines) + "\n"
        return str(item.get("input") or "")
