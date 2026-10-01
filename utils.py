import re
import math
from typing import Any, Dict, List, Optional
from models import RouteDecision
from config import SKILL_ALIASES, PERSIAN_RE, PERSIAN_DIGIT_MAP, ARABIC_DIGIT_MAP

def trim_text(text: str, max_chars: int) -> str:
    text = text or ""
    return text if len(text) <= max_chars else text[:max_chars] + "\n[TRUNCATED]"

def contains_persian(text: str) -> bool:
    return bool(PERSIAN_RE.search(text or ""))

def normalize_digits(text: str) -> str:
    text = text or ""
    return text.translate(PERSIAN_DIGIT_MAP).translate(ARABIC_DIGIT_MAP)

def normalize_skill(value: Any) -> Optional[str]:
    if not isinstance(value, str): return None
    cleaned = value.strip().lower().replace(" ", "_").replace("-", "_")
    if cleaned in SKILL_ALIASES: return SKILL_ALIASES[cleaned]
    for alias, skill in SKILL_ALIASES.items():
        if alias in cleaned: return skill
    return None

def normalize_route(raw: Dict[str, Any]) -> RouteDecision:
    if not isinstance(raw, dict): raw = {}
    skills_raw = raw.get("skills") or raw.get("skill", [])
    if isinstance(skills_raw, str):
        skills_raw = [part.strip() for part in skills_raw.split(",")] if "," in skills_raw else [skills_raw]
    if not isinstance(skills_raw, list): skills_raw = []

    normalized_skills = []
    for item in skills_raw:
        skill = normalize_skill(item)
        if skill and skill not in normalized_skills: normalized_skills.append(skill)

    specific_skills = [s for s in normalized_skills if s != "general_chat"]
    if specific_skills: normalized_skills = specific_skills
    normalized_skills = normalized_skills[:2]

    target_language = raw.get("target_language") or raw.get("target") or raw.get("language")
    if isinstance(target_language, list): target_language = " ".join(str(x) for x in target_language)
    if target_language is not None:
        target_language = str(target_language).strip()
        if target_language.lower() in {"", "none", "null"}: target_language = None

    return RouteDecision(
        skills=normalized_skills,
        target_language=target_language,
        reasoning=str(raw.get("reasoning") or raw.get("reason") or "")
    )

def format_number(value: float) -> str:
    if isinstance(value, bool): return str(int(value))
    if isinstance(value, float):
        if math.isfinite(value) and math.isclose(value, round(value), rel_tol=1e-12, abs_tol=1e-12):
            return str(int(round(value)))
        return f"{value:.10g}"
    return str(value)