from .approval_tools import approve_request, check_pending_approvals, reject_request
from .finance_tools import check_expense_status, request_advance_payment, submit_expense_report
from .hr_tools import check_leave_balance, check_salary_slip, get_employee_info, request_leave
from .ifs_tools import lookup_part_detail, lookup_user_detail, lookup_user_info
from .it_tools import check_ticket_status, create_support_ticket, request_equipment
from .math_tools import calculate_wolfram
from .office_tools import get_lunch_menu, get_shuttle_times


DEPARTMENT_TOOLS = {
    "HR": [
        lookup_user_info,
        lookup_user_detail,
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
        lookup_part_detail,
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
        get_lunch_menu,
        get_shuttle_times,
    ],
}


def get_tools_for_agent(agent_name: str):
    dept = agent_name.replace("_Agent", "")
    return DEPARTMENT_TOOLS.get(dept, [])
