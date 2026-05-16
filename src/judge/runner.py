from __future__ import annotations

import os
import subprocess
import tempfile
import time

from .types import ExecutionResult


class PythonCodeRunner:
    def __init__(self, timeout_seconds: float = 3.0, python_executable: str = "python3"):
        self.timeout_seconds = timeout_seconds
        self.python_executable = python_executable

    def run(self, code: str, input_text: str, timeout_seconds: float | None = None) -> ExecutionResult:
        timeout = timeout_seconds or self.timeout_seconds
        temp_code_path = ""
        start = time.time()
        try:
            with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as file:
                file.write(code)
                temp_code_path = file.name

            process = subprocess.run(
                [self.python_executable, temp_code_path],
                input=input_text,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            elapsed_ms = (time.time() - start) * 1000
            return ExecutionResult(
                stdout=process.stdout,
                stderr=process.stderr,
                exit_code=process.returncode,
                elapsed_ms=elapsed_ms,
                timed_out=False,
            )
        except subprocess.TimeoutExpired as error:
            elapsed_ms = (time.time() - start) * 1000
            return ExecutionResult(
                stdout=error.stdout or "",
                stderr=error.stderr or "",
                exit_code=None,
                elapsed_ms=elapsed_ms,
                timed_out=True,
            )
        finally:
            if temp_code_path and os.path.exists(temp_code_path):
                os.remove(temp_code_path)

