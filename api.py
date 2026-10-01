from fastapi import APIRouter, HTTPException
from models import ChatRequest, ChatResponse
from graph import run_agent

router = APIRouter()

@router.post("/chat", response_model=ChatResponse, tags=["Agent"])
async def chat_endpoint(request: ChatRequest):
    """
    Send a prompt to the Multi-Skill Agent and receive the final response, 
    along with the routing decisions and intermediate skill outputs.
    """
    try:
        state = run_agent(request.prompt)
        return ChatResponse(
            final_response=state.get("final_response", ""),
            route=state.get("route"),
            skill_outputs=state.get("skill_outputs"),
            fallback=state.get("fallback", False)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))