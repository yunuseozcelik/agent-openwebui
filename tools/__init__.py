# tools/__init__.py

# 1. Alt modüllerden fonksiyonları çek
from .hr_tools import check_leave_balance, request_leave, check_salary_slip
from .it_tools import create_support_ticket, check_ticket_status, request_equipment
from .finance_tools import request_advance_payment, check_expense_status, submit_expense_report
from .approval_tools import check_pending_approvals, approve_request, reject_request

# --- YENİ: MATH TOOL IMPORT ---
from .math_tools import calculate_wolfram

# 2. Departmanlara göre paketle
DEPARTMENT_TOOLS = {
    "HR": [
        check_leave_balance,
        request_leave,
        check_salary_slip,
        check_pending_approvals, 
    ],
    
    "IT": [
        create_support_ticket,
        check_ticket_status,
        request_equipment,
    ],
    
    "Finance": [
        request_advance_payment,
        check_expense_status,
        submit_expense_report,
        approve_request, 
        reject_request
    ],

    # --- YENİ: MATH KATEGORİSİ ---
    "Math": [
        calculate_wolfram
    ]
}

def get_tools_for_agent(agent_name: str):
    dept = agent_name.replace("_Agent", "")
    return DEPARTMENT_TOOLS.get(dept, [])