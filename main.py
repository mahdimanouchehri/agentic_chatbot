import argparse
import uvicorn
from fastapi import FastAPI
from api import router as api_router
from graph import run_evaluation, run_agent

app = FastAPI(
    title="Multi-Skill Agent API",
    description="Modular LangGraph Agent with Summarization, Translation, Math, and Chat.",
    version="1.0.0"
)
app.include_router(api_router, prefix="/api/v1")

def main():
    parser = argparse.ArgumentParser(description="Multi-skill Agent Runner")
    parser.add_argument("--mode", choices=["api", "cli", "eval"], default="api", help="Run mode")
    parser.add_argument("--prompt", type=str, help="Run CLI with a single prompt")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="API host")
    parser.add_argument("--port", type=int, default=9595, help="API port")

    args = parser.parse_args()

    if args.mode == "eval":
        run_evaluation()
        return

    if args.mode == "cli":
        if args.prompt:
            state = run_agent(args.prompt)
            print("Agent:", state.get("final_response", ""))
        else:
            print("Multi-skill agent CLI ready. Type 'exit' to quit.")
            while True:
                try:
                    user_input = input("You: ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nExiting...")
                    break
                if not user_input or user_input.lower() in {"exit", "quit", "q"}:
                    break
                state = run_agent(user_input)
                print("Agent:", state.get("final_response", ""))
        return

    # Default mode: API
    print(f"Starting FastAPI server on http://{args.host}:{args.port}")
    print(f"Interactive API docs available at: http://{args.host}:{args.port}/docs")
    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()