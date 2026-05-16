from __future__ import annotations

from google import genai
from google.genai import types

import config

from .gemini_reference import get_judge_model_id
from .types import FirstFailedCase, HintLevel, ProblemContext
from .utils import extract_json_object, html_to_text


class GeminiHintGenerator:
    def __init__(self, model_id: str | None = None):
        self.model_id = model_id or get_judge_model_id()
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)

    def generate(self, problem: ProblemContext, code: str, failed_case: FirstFailedCase, hint_level: HintLevel) -> str:
        prompt = f"""
You are a Korean algorithm coach. Generate one helpful hint for a user whose Python code behaved differently
from the reference solution on an analysis-mode test. Do not reveal the full correct solution code.
Use polite Korean.

Hint level rules:
- level_1: very gentle hint; do not directly expose full input/output.
- level_2: explain the counterexample type.
- level_3: point to suspicious implementation areas in the user's code, but no final code.
- level_4: explain an approach close to the correct idea, but no complete code.

Return JSON only: {{"hint": "Korean hint text"}}

Problem ID: {problem.problem_id}
Title: {problem.title}
Problem summary:
{html_to_text(problem.description)[:2500]}

Hint level: {hint_level}

Failed test name: {failed_case.name}
Failed test reason: {failed_case.reason}
Input:
{failed_case.input}

Expected stdout:
{failed_case.expected}

Actual stdout:
{failed_case.actual}

User code:
```python
{code[:7000]}
```
"""
        response = self.client.models.generate_content(
            model=self.model_id,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.4),
        )
        parsed = extract_json_object(response.text or "")
        hint = str(parsed.get("hint") or "").strip()
        if not hint:
            hint = "이 케이스에서는 예제와 다른 경계 조건이 숨어 있습니다. 입력을 처리하는 흐름을 한 번 더 천천히 따라가 보시면 좋겠습니다."
        return hint

