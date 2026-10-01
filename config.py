import os
import re
from dotenv import load_dotenv

load_dotenv()

SKILLS = ["summarizer", "translator", "calculator", "general_chat"]
DEFAULT_MODEL = "qwen/qwen-2.5-7b-instruct:free"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"

PERSIAN_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")

# Using \uXXXX escapes to avoid any file encoding issues (UTF-8 vs Latin-1)
PERSIAN_DIGIT_MAP = str.maketrans("\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9", "0123456789")
ARABIC_DIGIT_MAP = str.maketrans("\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669", "0123456789")

SKILL_ALIASES = {
    "summarizer": "summarizer", "summary": "summarizer", "summarize": "summarizer", "summarise": "summarizer",
    "translator": "translator", "translate": "translator", "translation": "translator",
    "calculator": "calculator", "calc": "calculator", "calculate": "calculator", "math": "calculator", "mathematics": "calculator",
    "general_chat": "general_chat", "general": "general_chat", "chat": "general_chat", "conversation": "general_chat", "small_talk": "general_chat",
    
    # Persian/Aliases (Using unicode escapes for safety)
    "\u062e\u0644\u0627\u0635\u0647": "summarizer",                 # ?????
    "\u062e\u0644\u0627\u0635\u0647_\u06a9\u0646": "summarizer",     # ?????_??
    "\u062a\u0631\u062c\u0645\u0647": "translator",                 # ?????
    "\u062a\u0631\u062c\u0645\u0647_\u06a9\u0646": "translator",     # ?????_??
    "\u0645\u0627\u0634\u06cc\u0646_\u062d\u0633\u0627\u0628": "calculator", # ?????_????
    "\u0645\u062d\u0627\u0633\u0628\u0647": "calculator",           # ??????
    "\u0686\u062a": "general_chat",                                 # ??
    "\u06af\u0641\u062a\u06af\u0648": "general_chat",               # ?????
}