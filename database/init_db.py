import sqlite3
import os

DB_PATH = "./mydb.db"


def create_tables(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            employee_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            department TEXT,
            designation TEXT,
            manager_id INTEGER,
            date_of_joining TEXT,
            FOREIGN KEY (manager_id) REFERENCES employees(employee_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leave_balance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            leave_type TEXT NOT NULL,
            total_days REAL NOT NULL,
            used_days REAL NOT NULL DEFAULT 0,
            remaining_days REAL NOT NULL,
            FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leave_requests (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            leave_type TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            reason TEXT,
            applied_on TEXT NOT NULL,
            approved_by INTEGER,
            approved_on TEXT,
            FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
            FOREIGN KEY (approved_by) REFERENCES employees(employee_id)
        )
    """)


def seed_employees(cursor):
    employees = [
        (1001, "Soumyojit Sen",   "soumyojit@company.com", "Engineering",    "Systems Engineer",   1003, "2026-06-01"),
        (1002, "Priya Sharma",    "priya@company.com",     "HR",         "HR Executive",       1006, "2023-01-15"),
        (1003, "Arjun Mehta",     "arjun@company.com",     "Telecom",    "Project Manager",    1009, "2019-03-10"),
        (1004, "Kavita Nair",     "kavita@company.com",    "Finance",    "Financial Analyst",  1008, "2021-07-22"),
        (1005, "Rohan Kapoor",    "rohan@company.com",     "Telecom",    "Systems Engineer",   1003, "2026-06-01"),
        (1006, "Neha Iyer",       "neha@company.com",      "HR",         "HR Manager",         1009, "2018-02-11"),
        (1007, "Sameer Verma",    "sameer@company.com",    "Engineering","Backend Developer",  1008, "2020-11-05"),
        (1008, "Ananya Das",      "ananya@company.com",    "Telecom","Telecom Manager", 1009, "2017-09-18"),
        (1009, "Vikram Singh",    "vikram@company.com",    "Leadership", "VP Engineering",     None, "2015-04-01"),
        (1010, "Meera Iyengar",   "meera@company.com",     "Telecom",    "Systems Engineer",   1003, "2026-06-01"),
    ]

    cursor.executemany("""
        INSERT INTO employees
        (employee_id, name, email, department, designation, manager_id, date_of_joining)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, employees)


def seed_leave_balance(cursor):
    # (employee_id, leave_type, total_days, used_days)
    balances = [
        (1001, "casual", 12, 2),
        (1001, "sick",   10, 0),
        (1001, "earned", 15, 5),
        (1002, "casual", 12, 4),
        (1002, "sick",   10, 1),
        (1002, "earned", 15, 3),
        (1003, "casual", 12, 6),
        (1003, "sick",   10, 2),
        (1003, "earned", 15, 8),
        (1004, "casual", 12, 0),
        (1004, "sick",   10, 0),
        (1004, "earned", 15, 2),
        (1005, "casual", 12, 3),
        (1005, "sick",   10, 0),
        (1005, "earned", 15, 0),
    ]

    rows = [
        (emp_id, leave_type, total, used, total - used)
        for emp_id, leave_type, total, used in balances
    ]

    cursor.executemany("""
        INSERT INTO leave_balance
        (employee_id, leave_type, total_days, used_days, remaining_days)
        VALUES (?, ?, ?, ?, ?)
    """, rows)


def seed_leave_requests(cursor):
    # (employee_id, leave_type, start_date, end_date, status, reason, applied_on, approved_by, approved_on)
    requests = [
        (1001, "casual", "2026-08-15", "2026-08-16", "pending",  "Personal work",       "2026-08-01 10:00:00", None, None),
        (1001, "sick",   "2026-08-20", "2026-08-20", "approved", "Fever",               "2026-08-09 09:30:00", None, "2026-08-09 09:30:00"),
        (1002, "earned", "2026-09-01", "2026-09-05", "approved", "Family trip",         "2026-08-05 11:15:00", 1006, "2026-08-06 09:00:00"),
        (1003, "casual", "2026-08-25", "2026-08-25", "pending",  "Personal errand",     "2026-08-08 14:00:00", None, None),
        (1004, "sick",   "2026-08-07", "2026-08-07", "approved", "Migraine",            "2026-08-07 08:45:00", None, "2026-08-07 08:45:00"),
        (1005, "casual", "2026-08-18", "2026-08-19", "rejected", "Travel",              "2026-08-02 09:00:00", 1003, "2026-08-03 10:30:00"),
        (1006, "earned", "2026-09-10", "2026-09-12", "pending",  "Wedding",             "2026-08-09 12:00:00", None, None),
        (1007, "sick",   "2026-08-06", "2026-08-06", "approved", "Cold and cough",      "2026-08-06 07:50:00", None, "2026-08-06 07:50:00"),
        (1008, "casual", "2026-08-22", "2026-08-22", "pending",  "Personal work",       "2026-08-09 08:00:00", None, None),
        (1009, "earned", "2026-08-28", "2026-08-30", "approved", "Offsite",             "2026-08-04 16:00:00", None, "2026-08-04 16:00:00"),
        (1010, "sick",   "2026-08-09", "2026-08-09", "approved", "Fever",               "2026-08-09 07:30:00", None, "2026-08-09 07:30:00"),
    ]

    cursor.executemany("""
        INSERT INTO leave_requests
        (employee_id, leave_type, start_date, end_date, status, reason, applied_on, approved_by, approved_on)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, requests)


def init_db():
    if os.path.exists(DB_PATH):
        print(f"{DB_PATH} already exists. Delete it first if you want to reseed from scratch.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Creating tables...")
    create_tables(cursor)

    print("Seeding employees...")
    seed_employees(cursor)

    print("Seeding leave_balance...")
    seed_leave_balance(cursor)

    print("Seeding leave_requests...")
    seed_leave_requests(cursor)

    conn.commit()
    conn.close()
    print(f"Done. Database created at {DB_PATH}")


if __name__ == "__main__":
    init_db()