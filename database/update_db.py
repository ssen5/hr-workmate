import sqlite3
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "mydb.db")


def create_payroll_table():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payroll (
            payroll_id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            month TEXT NOT NULL,
            year INTEGER NOT NULL,
            basic_salary REAL NOT NULL,
            hra REAL NOT NULL,
            special_allowance REAL NOT NULL,
            gross_salary REAL NOT NULL,
            deductions REAL NOT NULL,
            net_salary REAL NOT NULL,
            payment_status TEXT NOT NULL DEFAULT 'pending',
            payment_date TEXT,
            FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
        )
    """)
    conn.commit()
    conn.close()
    print("payroll table created (or already exists).")


def seed_payroll():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # (employee_id, designation-based basic_salary)
    # basic salary roughly scaled by seniority/designation
    salary_map = [
        (1001, "Systems Engineer",     45000),
        (1002, "HR Executive",         40000),
        (1003, "Project Manager",      95000),
        (1004, "Financial Analyst",    55000),
        (1005, "Systems Engineer",     45000),
        (1006, "HR Manager",           80000),
        (1007, "Backend Developer",    65000),
        (1008, "Telecom Manager",      90000),
        (1009, "VP Engineering",       180000),
        (1010, "Systems Engineer",     45000),
    ]

    month = "August"
    year = 2026
    payroll_rows = []

    for employee_id, designation, basic in salary_map:
        hra = round(basic * 0.40, 2)               # 40% of basic
        special_allowance = round(basic * 0.15, 2)  # 15% of basic
        gross = basic + hra + special_allowance
        deductions = round(gross * 0.10, 2)         # flat 10% deductions (PF/tax combined)
        net = round(gross - deductions, 2)

        payroll_rows.append((
            employee_id, month, year,
            basic, hra, special_allowance,
            gross, deductions, net,
            "paid", "2026-08-01 09:00:00"
        ))

    cursor.executemany("""
        INSERT INTO payroll
        (employee_id, month, year, basic_salary, hra, special_allowance,
         gross_salary, deductions, net_salary, payment_status, payment_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, payroll_rows)

    conn.commit()
    conn.close()
    print(f"Seeded payroll for {len(payroll_rows)} employees ({month} {year}).")


if __name__ == "__main__":
    create_payroll_table()
    seed_payroll()


