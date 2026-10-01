from typing import Dict, Any, List
from langgraph.graph import END, START, StateGraph
from config import SKILLS
from models import AgentState, RouteDecision
from llm import ask_llm_text, ask_llm_json
from utils import trim_text, contains_persian, normalize_route, format_number
from math_utils import safe_eval_expression, extract_expression
from prompts import (ROUTER_SYSTEM_PROMPT, SUMMARIZER_SYSTEM_PROMPT, TRANSLATOR_SYSTEM_PROMPT, 
                     GENERAL_CHAT_SYSTEM_PROMPT, FALLBACK_SYSTEM_PROMPT, EVALUATION_SET)

def append_skill_output(state: AgentState, skill: str, output: str) -> List[Dict[str, str]]:
    outputs = list(state.get("skill_outputs") or [])
    outputs.append({"skill": skill, "output": output})
    return outputs

def next_skill_name(state: AgentState) -> str:
    route = state.get("route") or {}
    skills = route.get("skills") or []
    idx = int(state.get("skill_index", 0))
    if idx < len(skills):
        skill = skills[idx]
        return skill if skill in SKILLS else "general_chat"
    return "compose"

def router_node(state: AgentState) -> Dict[str, Any]:
    user_prompt = state.get("user_prompt", "")
    fallback = False
    try:
        raw_route = ask_llm_json(ROUTER_SYSTEM_PROMPT, f"User prompt:\n{trim_text(user_prompt, 2000)}\n\nReturn ONLY JSON.")
        route = normalize_route(raw_route)
        if not route.skills:
            fallback = True
            route = RouteDecision(skills=["general_chat"], target_language=route.target_language, reasoning="Fallback: no clear skill.")
    except Exception as exc:
        fallback = True
        route = RouteDecision(skills=["general_chat"], reasoning=f"Fallback: {exc}")

    return {"route": route.model_dump(), "skill_index": 0, "artifact": "", "skill_outputs": [], "final_response": "", "fallback": fallback, "error": None}

def summarize_node(state: AgentState) -> Dict[str, Any]:
    content = (state.get("artifact") or state.get("user_prompt", "")).strip()
    output = ask_llm_text(SUMMARIZER_SYSTEM_PROMPT, f"User request:\n{trim_text(state.get('user_prompt', ''), 1500)}\n\nContent:\n{trim_text(content, 8000)}") or "Summary could not be generated."
    return {"artifact": output, "skill_outputs": append_skill_output(state, "summarizer", output)}

def translator_node(state: AgentState) -> Dict[str, Any]:
    target_lang = (state.get("route") or {}).get("target_language") or "the requested language (default to English)"
    content = (state.get("artifact") or state.get("user_prompt", "")).strip()
    output = ask_llm_text(TRANSLATOR_SYSTEM_PROMPT, f"Target language: {target_lang}\n\nContent:\n{trim_text(content, 8000)}") or "Translation could not be generated."
    return {"artifact": output, "skill_outputs": append_skill_output(state, "translator", output)}

def calculator_node(state: AgentState) -> Dict[str, Any]:
    route = state.get("route") or {}
    is_last_skill = int(state.get("skill_index", 0)) >= len(route.get("skills") or []) - 1
    input_text = (state.get("artifact") or state.get("user_prompt", "")).strip()
    is_persian = contains_persian(state.get("user_prompt", ""))
    
    try:
        expression = extract_expression(input_text)
        if not expression:
            output = "????? ????? ????? ???? ???." if is_last_skill and is_persian else "I could not find a clear mathematical expression."
        else:
            result = safe_eval_expression(expression)
            formatted = format_number(result)
            output = f"????? ??????: {expression} = {formatted}" if is_last_skill and is_persian else f"Calculation result: {expression} = {formatted}"
    except Exception as exc:
        output = f"??? ?? ??????: {exc}" if is_last_skill and is_persian else f"Calculation error: {exc}"
        
    return {"artifact": output, "skill_outputs": append_skill_output(state, "calculator", output)}

def general_chat_node(state: AgentState) -> Dict[str, Any]:
    is_fallback = state.get("fallback", False)
    sys_prompt = FALLBACK_SYSTEM_PROMPT if is_fallback else GENERAL_CHAT_SYSTEM_PROMPT
    output = ask_llm_text(sys_prompt, f"User message:\n{trim_text(state.get('user_prompt', ''), 3000)}") or "Hello! How can I help?"
    return {"artifact": output, "skill_outputs": append_skill_output(state, "general_chat", output)}

def advance_node(state: AgentState) -> Dict[str, Any]:
    return {"skill_index": int(state.get("skill_index", 0)) + 1}

def compose_node(state: AgentState) -> Dict[str, Any]:
    return {"final_response": (state.get("artifact") or "I could not generate a response.").strip()}

def build_graph():
    graph = StateGraph(AgentState)
    for name, func in [("router", router_node), ("summarizer", summarize_node), ("translator", translator_node), 
                       ("calculator", calculator_node), ("general_chat", general_chat_node), 
                       ("advance", advance_node), ("compose", compose_node)]:
        graph.add_node(name, func)
        
    graph.add_edge(START, "router")
    cond_map = {s: s for s in SKILLS}
    cond_map["compose"] = "compose"
    
    graph.add_conditional_edges("router", next_skill_name, cond_map)
    for skill in SKILLS: graph.add_edge(skill, "advance")
    graph.add_conditional_edges("advance", next_skill_name, cond_map)
    graph.add_edge("compose", END)
    return graph.compile()

compiled_graph = build_graph()

def run_agent(prompt: str) -> Dict[str, Any]:
    initial_state: AgentState = {"user_prompt": prompt, "route": {}, "skill_index": 0, "artifact": "", "skill_outputs": [], "final_response": "", "fallback": False, "error": None}
    return compiled_graph.invoke(initial_state)

def route_prompt_only(prompt: str) -> List[str]:
    raw_route = ask_llm_json(ROUTER_SYSTEM_PROMPT, f"User prompt:\n{trim_text(prompt, 2000)}\n\nReturn ONLY JSON.")
    route = normalize_route(raw_route)
    return route.skills or ["general_chat"]

def run_evaluation() -> None:
    # ... (Keep your existing print logic for the EVALUATION_SET here) ...
    pass