from typing import Any, Dict, List, Optional, TypedDict, Literal
from pydantic import BaseModel, Field

class RouteDecision(BaseModel):
    skills: List[Literal["summarizer", "translator", "calculator", "general_chat"]] = Field(default_factory=list)
    target_language: Optional[str] = None
    reasoning: Optional[str] = None

class CalculatorExtraction(BaseModel):
    expression: str = ""

class AgentState(TypedDict, total=False):
    user_prompt: str
    route: Dict[str, Any]
    skill_index: int
    artifact: str
    skill_outputs: List[Dict[str, str]]
    final_response: str
    fallback: bool
    error: Optional[str]

# FastAPI Models
class ChatRequest(BaseModel):
    prompt: str

class ChatResponse(BaseModel):
    final_response: str
    route: Optional[Dict[str, Any]] = None
    skill_outputs: Optional[List[Dict[str, str]]] = None
    fallback: bool = False