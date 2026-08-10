import sqlite3
import os

import colorama

from datetime import datetime
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from rag.vectorstore import load_vectorstore

#from main import CURRENT_EMPLOYEE_ID as current_employee_id

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "mydb.db")

# ---------- Shared resources ----------

vectorstore = load_vectorstore()
retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

policy_prompt = ChatPromptTemplate.from_messages([
    ("system", """You're an HR assistant answering questions strictly from the company's HR policy document.

Context from the policy document:
{context}

Answer using only the context above. If the answer isn't in the context, say you don't have that information in the policy document — don't make anything up."""),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{question}")
])

db_answer_prompt = ChatPromptTemplate.from_messages([
    ("system", """You're an HR assistant. You were given raw database query results below.
Turn them into a short, clear, natural-language answer for the employee.
Don't mention SQL, tables, or that this came from a database — just answer plainly.
If the results are empty, say no matching records were found."""),
    ("human", "Original question: {question}\n\nRaw results: {raw_result}")
])


# ---------- Tools ----------

def make_tools(llm, chat_history, current_employee_id):

    @tool
    def read_hr_policy(question: str) -> str:
        """Search the HR policy document and answer questions about leave, benefits,
        code of conduct, working hours, or any other HR policy topic."""
        relevant_docs = retriever.invoke(question)
        context = "\n\n".join(doc.page_content for doc in relevant_docs)
        chain = policy_prompt | llm
        response = chain.invoke({
            "context": context,
            "question": question,
            "chat_history": chat_history
        })
        return response.content

    @tool
    def apply_for_leave(
        leave_type: str,
        start_date: str,
        end_date: str,
        reason: str = ""
    ) -> str:
        """Apply for leave for the currently logged-in employee.

        Args:
            leave_type: must be exactly one of 'casual', 'sick', or 'earned'
            start_date: leave start date in format YYYY-MM-DD
            end_date: leave end date in format YYYY-MM-DD
            reason: short reason for the leave (optional)

        Rules:
        - 'sick' leave is auto-approved instantly, no manager approval needed.
        - 'casual' and 'earned' leave are submitted as 'pending' and require manager approval.
        - Confirm leave_type, start_date, and end_date with the employee before calling
        this tool if any are ambiguous or missing.
        """
        employee_id = current_employee_id
        leave_type = leave_type.strip().lower()
        valid_types = ("casual", "sick", "earned")
        if leave_type not in valid_types:
            return f"Invalid leave type '{leave_type}'. Must be one of: {', '.join(valid_types)}."

        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            return "Invalid date format. Please use YYYY-MM-DD."

        if end < start:
            return "End date cannot be before start date."

        num_days = (end - start).days + 1

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM employees WHERE employee_id = ?", (employee_id,))
            employee = cursor.fetchone()
            if not employee:
                return f"No employee found with ID {employee_id}."

            cursor.execute(
                "SELECT * FROM leave_balance WHERE employee_id = ? AND leave_type = ?",
                (employee_id, leave_type)
            )
            balance = cursor.fetchone()
            if not balance:
                return f"No {leave_type} leave balance record found for this employee."

            if num_days > balance["remaining_days"]:
                return (
                    f"Cannot apply for {num_days} day(s) of {leave_type} leave — "
                    f"only {balance['remaining_days']} day(s) remaining."
                )

            applied_on = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if leave_type == "sick":
                status = "approved"
                approved_on = applied_on

                cursor.execute("""
                    INSERT INTO leave_requests
                    (employee_id, leave_type, start_date, end_date, status, reason, applied_on, approved_by, approved_on)
                    VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?)
                """, (employee_id, leave_type, start_date, end_date, status, reason, applied_on, approved_on))

                cursor.execute("""
                    UPDATE leave_balance
                    SET used_days = used_days + ?,
                        remaining_days = remaining_days - ?
                    WHERE employee_id = ? AND leave_type = ?
                """, (num_days, num_days, employee_id, leave_type))

                conn.commit()
                return (
                    f"Sick leave from {start_date} to {end_date} ({num_days} day(s)) "
                    f"auto-approved. Remaining sick balance: {balance['remaining_days'] - num_days} day(s)."
                )

            else:
                status = "pending"
                cursor.execute("""
                    INSERT INTO leave_requests
                    (employee_id, leave_type, start_date, end_date, status, reason, applied_on, approved_by, approved_on)
                    VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL)
                """, (employee_id, leave_type, start_date, end_date, status, reason, applied_on))

                conn.commit()
                cursor.execute("SELECT last_insert_rowid() AS rid")
                new_id = cursor.fetchone()["rid"]
                return (
                    f"{leave_type.capitalize()} leave request (ID {new_id}) from {start_date} to "
                    f"{end_date} ({num_days} day(s)) submitted and pending manager approval."
                )

        except Exception as e:
            conn.rollback()
            return f"Failed to submit leave request: {e}"
        finally:
            conn.close()

    @tool
    def approve_leave(request_id: int, decision: str) -> str:
        """Approve or reject a pending leave request. Only usable if the currently
        logged-in employee is the manager of the employee who submitted the request.

        Args:
            request_id: the ID of the leave_requests row to act on
            decision: must be exactly 'approve' or 'reject'
        """
        decision = decision.strip().lower()
        if decision not in ("approve", "reject"):
            return "Decision must be exactly 'approve' or 'reject'."

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM leave_requests WHERE request_id = ?", (request_id,))
            req = cursor.fetchone()
            if not req:
                return f"No leave request found with ID {request_id}."

            if req["status"] != "pending":
                return f"This request is already '{req['status']}' and cannot be changed."

            cursor.execute("SELECT * FROM employees WHERE employee_id = ?", (req["employee_id"],))
            requester = cursor.fetchone()
            if not requester:
                return "Requesting employee not found."

            if requester["manager_id"] != current_employee_id:
                return "You are not authorized to approve or reject this request — you are not this employee's manager."

            approved_on = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_status = "approved" if decision == "approve" else "rejected"

            cursor.execute("""
                UPDATE leave_requests
                SET status = ?, approved_by = ?, approved_on = ?
                WHERE request_id = ?
            """, (new_status, current_employee_id, approved_on, request_id))

            if new_status == "approved":
                start = datetime.strptime(req["start_date"], "%Y-%m-%d").date()
                end = datetime.strptime(req["end_date"], "%Y-%m-%d").date()
                num_days = (end - start).days + 1

                cursor.execute("""
                    UPDATE leave_balance
                    SET used_days = used_days + ?,
                        remaining_days = remaining_days - ?
                    WHERE employee_id = ? AND leave_type = ?
                """, (num_days, num_days, req["employee_id"], req["leave_type"]))

            conn.commit()
            return f"Leave request {request_id} has been {new_status}."

        except Exception as e:
            conn.rollback()
            return f"Failed to process approval: {e}"
        finally:
            conn.close()

    @tool
    def query_database(sql_query: str, original_question: str) -> str:
        """Run a READ-ONLY SQL SELECT query against the HR database to answer employee
        questions about leave balance, leave requests, payroll/salary, or employee records.

        Database schema:

        Table: employees
          - employee_id (INTEGER, primary key)
          - name (TEXT)
          - email (TEXT)
          - department (TEXT)
          - designation (TEXT)
          - manager_id (INTEGER, references employees.employee_id, nullable)
          - date_of_joining (TEXT, format YYYY-MM-DD)

        Table: leave_balance
          - id (INTEGER, primary key)
          - employee_id (INTEGER, references employees.employee_id)
          - leave_type (TEXT: 'casual', 'sick', or 'earned')
          - total_days (REAL)
          - used_days (REAL)
          - remaining_days (REAL)

        Table: leave_requests
          - request_id (INTEGER, primary key)
          - employee_id (INTEGER, references employees.employee_id)
          - leave_type (TEXT: 'casual', 'sick', or 'earned')
          - start_date (TEXT, format YYYY-MM-DD)
          - end_date (TEXT, format YYYY-MM-DD)
          - status (TEXT: 'pending', 'approved', or 'rejected')
          - reason (TEXT)
          - applied_on (TEXT, datetime)
          - approved_by (INTEGER, references employees.employee_id, nullable)
          - approved_on (TEXT, datetime, nullable)

        Table: payroll
          - payroll_id (INTEGER, primary key)
          - employee_id (INTEGER, references employees.employee_id)
          - month (TEXT, e.g. 'August')
          - year (INTEGER)
          - basic_salary (REAL)
          - hra (REAL)
          - special_allowance (REAL)
          - gross_salary (REAL)
          - deductions (REAL)
          - net_salary (REAL)
          - payment_status (TEXT: 'paid' or 'pending')
          - payment_date (TEXT, datetime, nullable)

        Rules:
        - Only generate SELECT statements. Never generate INSERT, UPDATE, DELETE, or DROP.
        - Always filter by employee_id when the question is about a specific person.
        - Use exact lowercase values for leave_type ('casual', 'sick', 'earned') and
          status ('pending', 'approved', 'rejected').
        - Use exact lowercase values for payment_status ('paid', 'pending').
        - When the question involves salary/payroll but doesn't specify a month/year,
          default to the most recent record (ORDER BY year DESC, and match month names

          against the current month if relevant) rather than assuming a specific one.
        - Also pass the employee's original question as `original_question`, so the
          result can be phrased back in plain language.
        """

        query_clean = sql_query.strip().rstrip(";")

        if not query_clean.lower().startswith("select"):
            return "Only SELECT queries are allowed for this tool."

        forbidden_keywords = ["insert", "update", "delete", "drop", "alter", "attach", "pragma"]
        if any(keyword in query_clean.lower() for keyword in forbidden_keywords):
            return "This query contains operations that are not allowed."

        if ";" in query_clean:
            return "Multiple statements are not allowed. Submit a single SELECT query."

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute(query_clean)
            rows = cursor.fetchall()
            raw_result = [dict(row) for row in rows]
        except Exception as e:
            return f"Query failed: {e}"
        finally:
            conn.close()

        # ---- Phrase raw_result in plain language ----
        chain = db_answer_prompt | llm
        response = chain.invoke({
            "question": original_question,
            "raw_result": str(raw_result)
        })
        return response.content

    return [read_hr_policy, apply_for_leave, approve_leave, query_database]