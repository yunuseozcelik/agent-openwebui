# tools/__init__.py

# 1. Alt modüllerden fonksiyonları çek
from .hr_tools import check_leave_balance, request_leave, check_salary_slip
from .it_tools import create_support_ticket, check_ticket_status, request_equipment
from .finance_tools import request_advance_payment, check_expense_status, submit_expense_report
from .approval_tools import check_pending_approvals, approve_request, reject_request

# (Eğer office_tools.py varsa onu da buraya ekleyebilirsin)
# from .office_tools import get_lunch_menu, get_shuttle_times

# 2. Departmanlara göre paketle
DEPARTMENT_TOOLS = {
    "HR": [
        check_leave_balance,
        request_leave,
        check_salary_slip,
        check_pending_approvals, # Onay tool'ları genelde HR veya Yöneticidedir
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
        approve_request, # Finansçı da onay verebilir
        reject_request
    ],
}

# 3. Yardımcı Fonksiyon (İlerde lazım olursa)
def get_tools_for_agent(agent_name: str):
    """Agent ismine göre (örn: HR_Agent) doğru tool listesini döner."""
    # "HR_Agent" stringinden "HR" kısmını ayıkla
    dept = agent_name.replace("_Agent", "")
    return DEPARTMENT_TOOLS.get(dept, [])