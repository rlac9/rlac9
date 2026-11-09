"""에이전트가 사용할 도구(tool) 모음.

도구는 평범한 파이썬 함수입니다. `@beta_tool` 데코레이터를 붙이면
SDK가 함수 이름, 타입 힌트, docstring을 읽어서 Claude에게 보낼
도구 설명(JSON 스키마)을 자동으로 만들어 줍니다.

그래서 docstring의 첫 줄(도구 설명)과 Args 부분(각 인자 설명)을
Claude가 이해하기 쉽게 쓰는 것이 중요합니다.
"""

from __future__ import annotations

import ast
import operator
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from anthropic import beta_tool

# 파일 도구가 접근할 수 있는 폴더 (이 파일이 있는 claude-agent 폴더).
# 이 폴더 밖의 파일은 읽을 수 없게 막습니다.
WORKSPACE = Path(__file__).resolve().parent

# 읽을 파일의 최대 크기 (너무 큰 파일은 잘라서 보냅니다)
MAX_READ_CHARS = 20_000


# ---------------------------------------------------------------------------
# 1) 계산기: eval()을 쓰지 않고 안전하게 사칙연산만 계산합니다.
# ---------------------------------------------------------------------------
_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(node: ast.AST) -> float | int:
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        left, right = _safe_eval(node.left), _safe_eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("지수가 너무 큽니다 (최대 100).")
        return _OPERATORS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("숫자와 + - * / // % ** ( ) 만 사용할 수 있습니다.")


def calculate_expression(expression: str) -> str:
    """계산 로직 (도구와 테스트에서 함께 사용)."""
    tree = ast.parse(expression, mode="eval")
    result = _safe_eval(tree)
    return str(result)


@beta_tool
def calculate(expression: str) -> str:
    """수학 식을 정확하게 계산합니다. 큰 수의 곱셈이나 복잡한 계산에 사용하세요.

    Args:
        expression: 계산할 식. 예: "123 * 456", "(3 + 4) ** 2 / 7"
    """
    return calculate_expression(expression)


# ---------------------------------------------------------------------------
# 2) 현재 시각
# ---------------------------------------------------------------------------
def current_time(timezone: str = "Asia/Seoul") -> str:
    try:
        tz = ZoneInfo(timezone)
    except ZoneInfoNotFoundError as err:
        raise ValueError(f"알 수 없는 시간대입니다: {timezone}") from err
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S (%A) %Z")


@beta_tool
def get_current_time(timezone: str = "Asia/Seoul") -> str:
    """지정한 시간대의 현재 날짜와 시각을 알려줍니다.

    Args:
        timezone: IANA 시간대 이름. 예: "Asia/Seoul", "America/New_York", "UTC"
    """
    return current_time(timezone)


# ---------------------------------------------------------------------------
# 3) 파일 목록 / 파일 읽기 (읽기 전용, WORKSPACE 폴더 안에서만)
# ---------------------------------------------------------------------------
def _resolve_in_workspace(path: str) -> Path:
    """경로가 WORKSPACE 밖을 가리키면 에러를 냅니다 (예: ../../etc/passwd 차단)."""
    target = (WORKSPACE / path).resolve()
    if not target.is_relative_to(WORKSPACE):
        raise PermissionError("작업 폴더 밖의 파일에는 접근할 수 없습니다.")
    return target


def list_directory(directory: str = ".") -> str:
    target = _resolve_in_workspace(directory)
    if not target.is_dir():
        raise FileNotFoundError(f"폴더가 없습니다: {directory}")
    entries = []
    for item in sorted(target.iterdir()):
        if item.name.startswith(".") or item.name == "__pycache__":
            continue
        entries.append(item.name + ("/" if item.is_dir() else ""))
    return "\n".join(entries) if entries else "(비어 있음)"


def read_text_file(path: str) -> str:
    target = _resolve_in_workspace(path)
    if not target.is_file():
        raise FileNotFoundError(f"파일이 없습니다: {path}")
    text = target.read_text(encoding="utf-8", errors="replace")
    if len(text) > MAX_READ_CHARS:
        text = text[:MAX_READ_CHARS] + f"\n... (파일이 길어서 {MAX_READ_CHARS}자까지만 보여줍니다)"
    return text


@beta_tool
def list_files(directory: str = ".") -> str:
    """작업 폴더 안의 파일과 하위 폴더 목록을 보여줍니다.

    Args:
        directory: 작업 폴더 기준 상대 경로. 기본값은 "." (작업 폴더 자체)
    """
    return list_directory(directory)


@beta_tool
def read_file(path: str) -> str:
    """작업 폴더 안의 텍스트 파일 내용을 읽습니다.

    Args:
        path: 작업 폴더 기준 상대 경로. 예: "README.md", "notes/todo.txt"
    """
    return read_text_file(path)


# agent.py에서 사용할 도구 목록. 새 도구를 만들면 여기에 추가하세요.
ALL_TOOLS = [calculate, get_current_time, list_files, read_file]
