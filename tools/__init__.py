# tools/__init__.py

# Mevcut tool'lar
from .hr_tools import check_leave_balance, request_leave, check_salary_slip, get_employee_info
from .it_tools import create_support_ticket, check_ticket_status, request_equipment
from .finance_tools import request_advance_payment, check_expense_status, submit_expense_report
from .approval_tools import check_pending_approvals, approve_request, reject_request
from .math_tools import calculate_wolfram

# IFS tool'ları
from .ifs_tools import lookup_user_info, lookup_user_detail, lookup_part_detail, get_real_lunch_menu
from .office_tools import get_shuttle_times

DEPARTMENT_TOOLS = {
    "HR": [
        lookup_user_info,         # GERÇEK - IFS API (email ile kullanıcı bilgisi)
        lookup_user_detail,       # GERÇEK - IFS API (sicil no / email ile detay, izin bilgileri)
        check_leave_balance,
        get_employee_info,
        request_leave,
        check_salary_slip,
        check_pending_approvals,
    ],

    "IT": [
        create_support_ticket,
        check_ticket_status,
        request_equipment,
        lookup_part_detail,       # GERÇEK - IFS API
    ],

    "Finance": [
        request_advance_payment,
        check_expense_status,
        submit_expense_report,
        approve_request,
        reject_request,
    ],

    "Math": [
        calculate_wolfram,
    ],

    "General": [
        get_real_lunch_menu,      # GERÇEK - IFS API
        get_shuttle_times,        # mock (endpoint yok)
    ],
}


def get_tools_for_agent(agent_name: str):
    dept = agent_name.replace("_Agent", "")
    return DEPARTMENT_TOOLS.get(dept, [])
