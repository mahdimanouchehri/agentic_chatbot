import ast
import math
import operator
import re
from typing import Any
from pydantic import ValidationError

from config import PERSIAN_DIGIT_MAP, ARABIC_DIGIT_MAP
from models import CalculatorExtraction
from llm import ask_llm_json
from prompts import CALCULATOR_EXTRACT_SYSTEM_PROMPT
from utils import trim_text, normalize_digits

ALLOWED_BINARY_OPERATORS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow}
ALLOWED_UNARY_OPERATORS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
ALLOWED_FUNCTIONS = {"abs": abs, "round": round, "min": min, "max": max, "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan, "log": math.log, "log10": math.log10, "exp": math.exp, "pow": pow}
ALLOWED_CONSTANTS = {"pi": math.pi, "e": math.e, "tau": math.tau}

def normalize_math_expression(expr: str) -> str:
    expr = normalize_digits(expr or "")
    
    # Using \uXXXX escapes to avoid encoding issues
    expr = expr.replace("\u00d7", "*")  # × (Multiplication Sign)
    expr = expr.replace("\u00f7", "/")  # ÷ (Division Sign)
    expr = expr.replace("\u2212", "-")  # - (Minus Sign)
    expr = expr.replace("\u2014", "-")  # — (Em Dash)
    expr = expr.replace("^", "**")
    
    return re.sub(r"\s+", " ", expr).strip()

def _eval_ast(node: ast.AST) -> Any:
    if isinstance(node, ast.Expression): return _eval_ast(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool): raise ValueError("Boolean constants are not allowed.")
        if isinstance(node.value, (int, float)): return node.value
        raise ValueError("Only numeric constants are allowed.")
    if isinstance(node, ast.BinOp):
        op_func = ALLOWED_BINARY_OPERATORS.get(type(node.op))
        if not op_func: raise ValueError(f"Unsupported binary operator: {type(node.op).__name__}")
        return op_func(_eval_ast(node.left), _eval_ast(node.right))
    if isinstance(node, ast.UnaryOp):
        op_func = ALLOWED_UNARY_OPERATORS.get(type(node.op))
        if not op_func: raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
        return op_func(_eval_ast(node.operand))
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.keywords: raise ValueError("Invalid function call.")
        func_name = node.func.id
        if func_name not in ALLOWED_FUNCTIONS: raise ValueError(f"Function not allowed: {func_name}")
        return ALLOWED_FUNCTIONS[func_name](*[_eval_ast(arg) for arg in node.args])
    if isinstance(node, ast.Name):
        if node.id in ALLOWED_CONSTANTS: return ALLOWED_CONSTANTS[node.id]
        raise ValueError(f"Unknown name: {node.id}")
    raise ValueError(f"Unsupported syntax: {type(node).__name__}")

def safe_eval_expression(expression: str) -> float:
    expression = normalize_math_expression(expression)
    if not expression: raise ValueError("Empty expression.")
    if len(expression) > 500: raise ValueError("Expression is too long.")
    result = _eval_ast(ast.parse(expression, mode="eval"))
    if isinstance(result, (int, float)): return float(result)
    raise ValueError("Expression did not evaluate to a number.")

def regex_math_expression(text: str) -> str:
    text = normalize_digits(text or "")
    text = text.replace("\u00d7", "*").replace("\u00f7", "/").replace("^", "**")
    pattern = re.compile(r"(?:\b(?:sqrt|abs|round|min|max|sin|cos|tan|log|log10|exp|pow)\s*\([^()]*\)|\d+(?:\.\d+)?(?:\s*[-+*/%]\s*\d+(?:\.\d+)?)+)")
    match = pattern.search(text)
    return match.group(0).strip() if match else ""

def extract_expression(text: str) -> str:
    text = trim_text(text, 4000)
    try:
        raw = ask_llm_json(CALCULATOR_EXTRACT_SYSTEM_PROMPT, f"User request:\n{text}\n\nReturn ONLY JSON.")
        try: expr = CalculatorExtraction.model_validate(raw).expression.strip()
        except ValidationError: expr = str(raw.get("expression", "")).strip()
    except Exception: expr = ""
    if not expr: expr = regex_math_expression(text)
    return normalize_math_expression(expr)