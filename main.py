import os
import colorama

from dotenv import load_dotenv

from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq

from datetime import datetime


from tools import make_tools
from rag.vectorstore import CHROMA_DIR

load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")

llm = ChatGroq(
    groq_api_key=groq_api_key,
    model_name="openai/gpt-oss-120b"
)

if not os.path.exists(CHROMA_DIR):
    raise RuntimeError(
        f"No vectorstore found at {CHROMA_DIR}. Run `python ingest.py` first."
    )

# ---------- Hardcoded session identity (prototype stage) ----------
os.system("cls" if os.name == "nt" else "clear")

CURRENT_EMPLOYEE_ID = int(input("Enter Employee ID: "))

# ---------- Chat history ----------

chat_history = []  # list of HumanMessage / AIMessage objects

# ---------- Tools ----------

tools = make_tools(llm, chat_history, CURRENT_EMPLOYEE_ID)
llm_with_tools = llm.bind_tools(tools)
tool_map = {t.name: t for t in tools}

# ---------- Main prompt (history-aware, identity-aware) ----------

today_date = datetime.now().strftime("%Y-%m-%d")

main_prompt = ChatPromptTemplate.from_messages([
    ("system", f"""You are an HR assistant for employees.

                    Today's date is {today_date}.
                    When calculating relative dates like "tomorrow" or "next week", use this as the reference point.

                    The employee you are currently talking to has employee_id={CURRENT_EMPLOYEE_ID}.
                    Always use this employee_id for any database lookup or action — never ask the
                    employee for their ID or email, you already know it.

                    Use your tools to answer HR policy questions, database lookups (leave balance,
                    leave requests, payroll/salary details), or actions (like applying for leave
                    or approving/rejecting leave requests). For anything unrelated to HR, politely
                    say you can only help with HR-related topics."""),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}")
])

chain_with_tools = main_prompt | llm_with_tools

# ---------- Main loop ----------

#os.system("cls" if os.name == "nt" else "clear")

def main():
    print(f"HR Assistant ready (employee_id={CURRENT_EMPLOYEE_ID}). Type 'exit' to quit.\n")

    while True:
        information = input(colorama.Fore.GREEN + "You: ")
        if information.strip().lower() == "exit":
            break

        response = chain_with_tools.invoke({
            "input": information,
            "chat_history": chat_history
        })

        WRITE_TOOLS = ("apply_for_leave", "approve_leave")

        if response.tool_calls:
            answers = []
            for call in response.tool_calls:
                tool_fn = tool_map.get(call["name"])

                if not tool_fn:
                    answers.append(f"(No handler wired up for tool: {call['name']})")
                    continue

                if call["name"] in WRITE_TOOLS:
                    print(f"\nThis will run: {call['name']} with {call['args']}")
                    confirm = input("Proceed? (yes/no): ").strip().lower()
                    if confirm not in ("yes", "y"):
                        answers.append(f"Cancelled: {call['name']} was not executed.")
                        continue

                result = tool_fn.invoke(call["args"])
                answers.append(result)

            answer = "\n\n".join(answers)
        else:
            answer = response.content

        print(colorama.Fore.WHITE + f"\nBot: {answer}\n")

        chat_history.append(HumanMessage(content=information))
        chat_history.append(AIMessage(content=answer))


if __name__ == "__main__":
    main()