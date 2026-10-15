"""One-time patch: replaces the eval-based calculator in agent/agent_core.py with a safe arithmetic evaluator.

Run from the module-1-ai-agents folder:  python apply_calculator_fix.py
A backup is saved as agent/agent_core.py.bak. Delete this script afterwards (do not commit it).
"""
import re
import sys
from pathlib import Path

TARGET = Path(__file__).resolve().parent / "agent" / "agent_core.py"

NEW_BLOCK = '''_THOUSANDS = re.compile(r"(?<![\\d.,])\\d{1,3}(?:,\\d{3})+(?![\\d,])")
_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_MAX_EXPONENT = 100
_MAX_LENGTH = 200


class _UnsupportedExpression(Exception):
    """Raised when an expression uses anything beyond plain arithmetic."""


def _eval_node(node):
    """Evaluate a parsed expression, allowing only numbers, + - * / // ** and parentheses."""
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > _MAX_EXPONENT:
            raise ValueError("exponent too large")
        return _BIN_OPS[type(node.op)](left, right)
    raise _UnsupportedExpression()


@tool
def calculate(expression: str) -> str:
    """
    Evaluate a mathematical expression.
    Input: a string with only numbers and operators like: 150000 * 0.15
    Thousands separators such as 1,000 are accepted.
    """
    try:
        if len(expression) > _MAX_LENGTH:
            return "Error: expression too long"
        allowed = set("0123456789+-*/()., ")
        if not all(c in allowed for c in expression):
            return "Error: unsafe characters in expression"
        cleaned = _THOUSANDS.sub(lambda m: m.group().replace(",", ""), expression)
        result = _eval_node(ast.parse(cleaned.strip(), mode="eval"))
        return f"Result: {result}"
    except _UnsupportedExpression:
        return "Error: unsupported expression"
    except Exception as e:
        return f"Calculation error: {e}"
'''


def main() -> int:
    if not TARGET.exists():
        print(f"Cannot find {TARGET}. Run this script from the module-1-ai-agents folder.")
        return 1
    text = TARGET.read_text(encoding="utf-8")
    if "_eval_node" in text:
        print("Already patched. Nothing to do.")
        return 0

    pattern = re.compile(r"@tool\s+def calculate\(expression: str\) -> str:.*?(?=\n@tool\s+def search_web)", re.DOTALL)
    if not pattern.search(text):
        print("Could not find the calculate function followed by search_web. No changes made.")
        return 1

    Path(str(TARGET) + ".bak").write_text(text, encoding="utf-8")
    text = pattern.sub(lambda m: NEW_BLOCK.rstrip("\n") + "\n", text, count=1)

    for module in ("ast", "operator", "re"):
        if not re.search(rf"^import {module}\s*$", text, re.MULTILINE):
            text = re.sub(r"^import os\s*$", f"import {module}\nimport os", text, count=1, flags=re.MULTILINE)
    TARGET.write_text(text, encoding="utf-8")
    print("Patched agent/agent_core.py. Backup saved as agent/agent_core.py.bak")
    return 0


if __name__ == "__main__":
    sys.exit(main())