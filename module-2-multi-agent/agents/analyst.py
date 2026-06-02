"""
Module 2: Analyst Agent
Author: Geoffrey Jones Okwi | AI/ML Engineer
Role: Data analysis, salary calculations, skill gap analysis, job market intelligence
"""

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool

load_dotenv()


# ─────────────────────────────────────────
# ANALYST TOOLS
# ─────────────────────────────────────────
@tool
def calculate(expression: str) -> str:
    """
    Safely evaluate a math expression.
    Input: numbers and operators only e.g. '150000 * 0.15'
    """
    try:
        allowed = set("0123456789+-*/()., ")
        if not all(c in allowed for c in expression):
            return "Error: unsafe characters"
        result = eval(expression)  # noqa: S307
        return f"Result: {result}"
    except Exception as e:
        return f"Calculation error: {e}"


@tool
def salary_analyzer(role: str, experience_years: int = 3) -> str:
    """
    Analyze salary ranges and career trajectory for AI/ML roles.
    Input: role name and years of experience.
    """
    salary_db = {
        "ai engineer": {
            "junior":   {"range": "$90K–$120K",  "years": "0–2"},
            "mid":      {"range": "$130K–$160K",  "years": "3–5"},
            "senior":   {"range": "$170K–$220K",  "years": "6–10"},
            "staff":    {"range": "$220K–$300K+", "years": "10+"},
        },
        "ml engineer": {
            "junior":   {"range": "$95K–$125K",  "years": "0–2"},
            "mid":      {"range": "$140K–$170K",  "years": "3–5"},
            "senior":   {"range": "$180K–$230K",  "years": "6–10"},
            "staff":    {"range": "$230K–$320K+", "years": "10+"},
        },
        "ai consultant": {
            "junior":   {"range": "$80K–$110K",   "years": "0–2"},
            "mid":      {"range": "$120K–$160K",  "years": "3–5"},
            "senior":   {"range": "$170K–$220K",  "years": "6–10"},
            "contract": {"range": "$150K–$300K",  "years": "Any"},
        },
        "data scientist": {
            "junior":   {"range": "$80K–$105K",  "years": "0–2"},
            "mid":      {"range": "$115K–$145K",  "years": "3–5"},
            "senior":   {"range": "$150K–$190K",  "years": "6–10"},
            "staff":    {"range": "$190K–$250K+", "years": "10+"},
        },
    }

    key = role.lower().strip()
    data = None
    for k, v in salary_db.items():
        if k in key or key in k:
            data = v
            break

    if not data:
        return f"Role '{role}' not in database. General AI/ML: $120K–$200K depending on seniority."

    # Determine level by experience
    if experience_years <= 2:
        level = "junior"
    elif experience_years <= 5:
        level = "mid"
    elif experience_years <= 9:
        level = "senior"
    else:
        level = "staff"

    level_data = data.get(level, data.get("mid", {}))

    return (
        f"💰 {role.title()} — {level.title()} Level ({experience_years} yrs exp)\n"
        f"   Salary Range: {level_data.get('range', 'N/A')}\n"
        f"   Typical Years at Level: {level_data.get('years', 'N/A')}\n\n"
        f"📈 Full Career Trajectory:\n"
        + "\n".join(
            f"   {lvl.title()}: {info['range']} ({info['years']} yrs)"
            for lvl, info in data.items()
        )
    )


@tool
def skill_gap_analyzer(current_skills: str, target_role: str) -> str:
    """
    Analyze skill gaps between current skills and target AI/ML role requirements.
    Input: comma-separated current skills and target role name.
    """
    role_requirements = {
        "ai engineer":    ["LangChain", "LangGraph", "Docker", "AWS", "RAG", "Python", "FastAPI", "CI/CD", "FAISS"],
        "ml engineer":    ["PyTorch", "TensorFlow", "MLflow", "Kubernetes", "Spark", "Python", "Docker", "SQL"],
        "ai consultant":  ["LangChain", "RAG", "Prompt Engineering", "AWS", "Azure", "Client Communication", "Python"],
        "data scientist": ["Python", "SQL", "Pandas", "Scikit-learn", "Statistics", "Tableau", "ML", "Storytelling"],
        "senior ai engineer": ["LangChain", "LangGraph", "Docker", "AWS", "System Design", "MLOps", "Mentoring", "RAG"],
    }

    key = target_role.lower().strip()
    required = None
    for k, v in role_requirements.items():
        if k in key or key in k:
            required = v
            break

    if not required:
        return f"Role '{target_role}' not found. Try: AI Engineer, ML Engineer, AI Consultant, Data Scientist."

    current = [s.strip() for s in current_skills.split(",")]
    current_lower = [s.lower() for s in current]

    have = [r for r in required if r.lower() in current_lower]
    missing = [r for r in required if r.lower() not in current_lower]

    pct = int((len(have) / len(required)) * 100)

    return (
        f"🎯 Skill Gap Analysis: {target_role.title()}\n\n"
        f"✅ You already have ({len(have)}/{len(required)} — {pct}%):\n"
        f"   {', '.join(have) if have else 'None matched yet'}\n\n"
        f"📚 Skills to learn ({len(missing)} remaining):\n"
        f"   {', '.join(missing)}\n\n"
        f"{'🔥 You are job-ready! Apply now.' if pct >= 70 else '💪 Keep building — you are on the right track!'}"
    )


ANALYST_TOOLS = [calculate, salary_analyzer, skill_gap_analyzer]


# ─────────────────────────────────────────
# ANALYST SYSTEM PROMPT
# ─────────────────────────────────────────
ANALYST_PROMPT = """You are an AI/ML Career Analyst Agent built by Geoffrey Jones Okwi.

Your specialties:
- Salary analysis and negotiation data
- Skill gap analysis for AI/ML roles
- Mathematical calculations
- Job market trend analysis

RULES:
- Use salary_analyzer for any salary or compensation questions
- Use skill_gap_analyzer when user lists their skills and asks about a role
- Use calculate for any math
- Give structured, actionable answers
- Always end with 1 clear next action the user should take
"""


# ─────────────────────────────────────────
# ANALYST NODE FUNCTION
# ─────────────────────────────────────────
def analyst_node(state: dict) -> dict:
    """Analyst agent — salary, skills, calculations."""
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.1,
        max_tokens=1024,
    )
    llm_with_tools = llm.bind_tools(ANALYST_TOOLS, parallel_tool_calls=False)

    task = state.get("task", "")
    messages = [
        SystemMessage(content=ANALYST_PROMPT),
        HumanMessage(content=task),
    ]

    # ReAct loop
    for _ in range(4):
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        if not (hasattr(response, "tool_calls") and response.tool_calls):
            break

        for tc in response.tool_calls:
            tool_map = {
                "calculate":          calculate,
                "salary_analyzer":    salary_analyzer,
                "skill_gap_analyzer": skill_gap_analyzer,
            }
            tool_fn = tool_map.get(tc["name"])
            if tool_fn:
                result = tool_fn.invoke(tc["args"])
                messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))

    final = messages[-1].content if hasattr(messages[-1], "content") else str(messages[-1])
    if isinstance(final, list):
        final = " ".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in final)

    results = state.get("results", {})
    results["analyst"] = final

    return {
        **state,
        "messages": [response],
        "results": results,
        "next_agent": "finish",
    }