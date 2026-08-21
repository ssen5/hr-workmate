import os
from datetime import datetime

import colorama
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage, AIMessage
from langchain_groq import ChatGroq
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from tools import make_tools
from rag.vectorstore import CHROMA_DIR

load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")

llm = ChatGroq(
    groq_api_key=groq_api_key,
    model_name="openai/gpt-oss-120b",
    temperature=0
)

if not os.path.exists(CHROMA_DIR):
    raise RuntimeError(
        f"No vectorstore found at {CHROMA_DIR}. Run `python ingest.py` first."
    )

# ---------- Hardcoded session identity (prototype stage) ----------
os.system("cls" if os.name == "nt" else "clear")

CURRENT_EMPLOYEE_ID = int(input("Enter Employee ID: "))

# ---------- Tools ----------
chat_history_for_tools = []

tools = make_tools(llm, chat_history_for_tools, CURRENT_EMPLOYEE_ID)

today_date = datetime.now().strftime("%Y-%m-%d")

SYSTEM_PROMPT = f"""You are an HR assistant for employees.

Today's date is {today_date}.
When calculating relative dates like "tomorrow" or "next week", use this as the reference point.

The employee you are currently talking to has employee_id={CURRENT_EMPLOYEE_ID}.
Always use this employee_id for any database lookup or action — never ask the
employee for their ID or email, you already know it.

Use your tools to answer HR policy questions, database lookups (leave balance,
leave requests, payroll/salary details), or actions (like applying for leave
or approving/rejecting leave requests). For anything unrelated to HR, politely
say you can only help with HR-related topics.

IMPORTANT — confirming write actions:
Before calling apply_for_leave or approve_leave, do NOT call the tool yet.
Instead, reply in plain text summarizing exactly what you are about to do
(the action and its key details) and ask the employee to confirm, e.g.
"Should I go ahead and apply for leave from X to Y?"
Only call the tool once the employee has clearly confirmed (e.g. said yes,
confirm, go ahead) in a later message. If they decline or say no, do not
call the tool — acknowledge that you won't proceed."""

# ---------- Agent ----------

checkpointer = InMemorySaver()

agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
)

# ---------- Main loop ----------

def main():
    print(f"HR Assistant ready (employee_id={CURRENT_EMPLOYEE_ID}). Type 'exit' to quit.\n")

    config = {"configurable": {"thread_id": str(CURRENT_EMPLOYEE_ID)}}

    while True:
        information = input(colorama.Fore.GREEN + "You: ")
        if information.strip().lower() == "exit":
            break

        result = agent.invoke(
            {"messages": [HumanMessage(content=information)]},
            config=config
        )

        final_message = result["messages"][-1]
        answer = final_message.content

        print(colorama.Fore.WHITE + f"\nBot: {answer}\n")

        chat_history_for_tools.append(HumanMessage(content=information))
        chat_history_for_tools.append(AIMessage(content=answer))


if __name__ == "__main__":
    main()