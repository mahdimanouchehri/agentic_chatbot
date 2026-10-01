

***

# 🧠 Multi-Skill LangGraph Agent

A production-ready, modular AI agent built with **LangGraph** and **FastAPI**. It uses a router-based architecture to dynamically chain multiple skills (Summarization, Translation, Calculator, General Chat) based on user intent. It features native support for the Persian language, robust AST-based safe math evaluation, and exposes a RESTful API for seamless integration.

---

## 🚀 1. How to Run the Project

### Prerequisites
- Python 3.10 or higher
- An OpenRouter API Key (Free tier available)

### Installation
```bash
# Clone the repository and navigate to the folder
cd test_agentic_simple_project

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Variables
Create a `.env` file in the root directory and add your OpenRouter credentials:
```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_MODEL=liquid/lfm-2.5-2.6b:free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

### Run Commands
**Start the FastAPI Server (Default):**
```bash
python main.py
# Server will be available at http://localhost:8000
# Interactive Swagger UI docs: http://localhost:8000/docs
```

**Run via CLI:**
```bash
python main.py --mode cli
# Or run a single prompt:
python main.py --mode cli --prompt "What is 15 * 4?"
```

**Run Evaluation Suite:**
```bash
python main.py --mode eval
```

---

## 🏗️ 2. Graph Architecture

The agent is powered by **LangGraph**, utilizing a stateful cyclic graph to handle sequential skill execution.

### Nodes
1. **`router`**: Analyzes the user prompt and outputs a JSON `RouteDecision` (skills list, target language).
2. **`summarizer` / `translator` / `calculator` / `general_chat`**: Execution nodes that process the current state `artifact`.
3. **`advance`**: Increments the `skill_index` to move to the next skill in the chain.
4. **`compose`**: Finalizes the `artifact` into the `final_response`.

### Decision Flow
`START` ➡️ `router` ➡️ *(Conditional Edge)* ➡️ `Skill Node` ➡️ `advance` ➡️ *(Conditional Edge loops back to next skill or goes to compose)* ➡️ `compose` ➡️ `END`

### Reasoning Behind Design Decisions
- **Sequential Chaining via `advance`**: Instead of a massive single prompt trying to "summarize and translate", we pass the output (`artifact`) of Skill A as the input to Skill B. This drastically improves accuracy for small-parameter models.
- **Safe Math AST**: The `calculator` node does *not* use `eval()`. It parses the LLM's extracted string into an Abstract Syntax Tree (AST) and evaluates it against a strict whitelist of operators/functions to prevent arbitrary code execution.
- **State Normalization**: The `AgentState` TypedDict ensures that every node knows exactly what data is available, preventing hallucinated state mutations.

---

## ✍️ 3. Prompt Engineering Process

### Strategy
Prompts are engineered using the **Role-Task-Constraint** framework. 
1. **Role**: "You are a routing node..."
2. **Task**: "Analyze the prompt and return JSON..."
3. **Constraints**: "Do not use markdown. Max 2 skills. Use Latin digits."

### Documented Prompt-Improvement Example: The Router Node

**Initial Version (Failed on Multi-Skill & Persian):**
> *Prompt:* "Look at the user prompt and decide if they want to summarize, translate, calculate, or chat. Return a JSON object with the skill name."
* **Issue:** The model would return `{"skill": "summarize, translate"}` (a single string instead of a list), fail to order the skills correctly, and ignored Persian inputs entirely.

**Final Version (Current Implementation):**
> *Prompt:* "You are the routing node... You must return ONLY a valid JSON object. Choose at most 2 skills. Put skills in the correct execution order (e.g., summarize then translate). Understand Persian prompts correctly..."
* **Why it changed:** By explicitly defining the JSON schema, enforcing an array `["skill1", "skill2"]`, and adding specific few-shot examples for Persian and multi-skill chains, the 2.6B model's routing accuracy jumped from ~60% to >90%.

---

## 🔗 4. Multi-Skill & Fallback Handling

### Multi-Skill Case (e.g., "Summarize this and translate it to English")
1. The `router` extracts an ordered list: `["summarizer", "translator"]`.
2. The graph routes to `summarizer`. The output text is saved to the `artifact` state variable.
3. The `advance` node increments `skill_index` from 0 to 1.
4. The graph routes to `translator`, which reads the *previous artifact* (the summary) rather than the raw user prompt, and translates it.

### Fallback Behavior
If the `router` fails to parse JSON, or returns an empty skills list `[]` (highly ambiguous prompt), the `router_node` catches the exception/empty state, sets `fallback=True`, and forces the route to `general_chat`. The `general_chat` node detects the `fallback` flag and switches to the `FALLBACK_SYSTEM_PROMPT`, which politely asks the user to clarify their request while listing the agent's capabilities.

---


## 🤖 5. LLM Provider & Model

- **Provider:** OpenRouter
- **Model:** `liquid/lfm-2.5-2.6b:free` (Liquid LFM 2.5)
- **Confirmation:** This model is explicitly on the **Free Tier** and has **2.6 Billion parameters**, which strictly satisfies the requirement of being $\le$ 35B parameters. It was chosen for its high instruction-following capabilities relative to its small size, making it highly cost-effective and fast for routing and simple text transformations.

---

## 🇮🇷 6. Persian Language Handling

Handling Persian requires addressing both text and mathematical inputs:
1. **Digit Normalization:** Users often type Persian (`۰۱۲۳۴۵۶۷۸۹`) or Arabic (`٠١٢٣٤٥٦٧٨٩`) digits. A translation map (`PERSIAN_DIGIT_MAP`) converts these to standard Latin digits (`0-9`) *before* they are passed to the AST math evaluator.
2. **Regex Detection:** `contains_persian()` uses Unicode ranges (`\u0600-\u06FF`) to detect if the prompt is in Persian.
3. **Context-Aware Output:** If the prompt is detected as Persian, the `calculator_node` overrides its default English output strings and returns localized Persian error messages (e.g., `"خطا در محاسبه"` instead of `"Calculation error"`).
4. **Prompt Instructions:** The `summarizer` and `translator` system prompts explicitly instruct the LLM to preserve Persian syntax and generate natural, fluent Persian text when applicable.

---

## ⚠️ 7. Known Limitations & Production Readiness

### Current Limitations
- **No Conversational Memory:** The agent is single-turn. It does not remember previous prompts.
- **No Streaming:** The FastAPI endpoint waits for the entire LangGraph execution to finish before returning the JSON response.
- **Math Complexity:** The AST evaluator handles arithmetic and standard functions (`sqrt`, `sin`), but cannot solve symbolic algebra or calculus.

### What is Needed for Production?
1. **Memory/State Store:** Implement Redis or PostgreSQL to store `thread_id` histories for multi-turn conversations.
2. **Streaming (SSE):** Update FastAPI to use `StreamingResponse` and LangGraph's `astream_events` to stream tokens to the UI in real-time.
3. **Security:** Add OAuth2/JWT authentication and Rate Limiting (e.g., `slowapi`) to the FastAPI routes.
4. **Observability:** Integrate LangSmith or Langfuse to trace LLM calls, monitor latency, and debug routing failures.
5. **Caching:** Implement semantic caching for the `router` and `calculator` nodes to save API costs on repeated queries.

---

## 🤔 8. Assumptions Made

- **Max Chain Length:** The brief did not specify how many skills could be chained. I assumed a maximum of **2 simultaneous skills** to prevent context-window degradation and infinite loops on small models.
- **Calculator Scope:** Assumed the calculator only needs to handle standard arithmetic, percentages, and basic trigonometry/logarithms, not complex symbolic mathematics.
- **Target Language Inference:** Assumed that if a user says "Translate to French" but the router misses the explicit JSON key, the translator node should default to English or infer it from the prompt text context.

---

## 🤖 9. AI Usage Disclosure

**Disclosure:** AI (Large Language Models) was actively utilized during the development of this project. Specifically, AI was used to:
1. Refactor the initial monolithic script into a clean, modular Python package structure.
2. Generate boilerplate FastAPI routing and Pydantic validation schemas.
3. Brainstorm edge cases for the AST math evaluator and Persian Unicode regex patterns.
4. Format and structure this README.md documentation.
