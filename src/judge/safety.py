from __future__ import annotations

import ast
from typing import Set

from .types import SafetyReport


class ReferenceSolutionSafetyChecker:
    blocked_modules: Set[str] = {
        "os",
        "subprocess",
        "socket",
        "requests",
        "urllib",
        "pathlib",
        "shutil",
        "glob",
        "pickle",
        "multiprocessing",
        "threading",
        "ctypes",
        "importlib",
    }
    allowed_modules: Set[str] = {
        "sys",
        "math",
        "collections",
        "heapq",
        "itertools",
        "bisect",
        "functools",
        "operator",
        "string",
        "array",
        "deque",
        "queue",
        "re",
        "copy",
        "decimal",
        "fractions",
        "statistics",
        "random",
    }
    blocked_calls: Set[str] = {"eval", "exec", "open", "compile", "__import__", "input.__globals__"}

    def check(self, code: str, strict_imports: bool = True) -> SafetyReport:
        errors = []
        warnings = []
        try:
            tree = ast.parse(code)
        except SyntaxError as error:
            return SafetyReport(ok=False, errors=[f"SyntaxError: {error.msg}"], warnings=[])

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_name = alias.name.split(".", 1)[0]
                    self._check_module(root_name, strict_imports, errors, warnings)
            elif isinstance(node, ast.ImportFrom):
                root_name = (node.module or "").split(".", 1)[0]
                if root_name:
                    self._check_module(root_name, strict_imports, errors, warnings)
            elif isinstance(node, ast.Call):
                call_name = self._call_name(node.func)
                if call_name in self.blocked_calls:
                    errors.append(f"위험 함수 호출이 감지되었습니다: {call_name}")
            elif isinstance(node, ast.Name):
                if node.id in {"__builtins__", "__loader__", "__spec__", "__file__"}:
                    warnings.append(f"특수 런타임 이름 사용이 감지되었습니다: {node.id}")
            elif isinstance(node, ast.While):
                if isinstance(node.test, ast.Constant) and node.test.value is True:
                    warnings.append("while True 패턴이 있어 timeout에 의존할 수 있습니다.")

        return SafetyReport(ok=not errors, errors=errors, warnings=warnings)

    def _check_module(self, module_name: str, strict_imports: bool, errors: list[str], warnings: list[str]) -> None:
        if module_name in self.blocked_modules:
            errors.append(f"위험 import가 감지되었습니다: {module_name}")
        elif strict_imports and module_name not in self.allowed_modules:
            warnings.append(f"허용 목록 밖 import가 감지되었습니다: {module_name}")

    def _call_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            owner = self._call_name(node.value)
            return f"{owner}.{node.attr}" if owner else node.attr
        return ""

