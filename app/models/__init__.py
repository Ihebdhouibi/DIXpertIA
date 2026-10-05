"""Model package.

Importing every model module here is deliberate, not tidiness. SQLAlchemy
resolves `relationship("Payslip")` by looking the name up in its registry, and a
class only enters that registry when its module is imported. Importing a subset
leaves the registry incomplete and the mapper fails at the first query with:

    expression 'Payslip' failed to locate a name

That is exactly what happened when #55 removed `from app.models.payroll import
Payslip` from main.py: nothing referenced Payslip directly any more, so the
import looked dead, and the relationships added in #60 then had nothing to
resolve against. Importing here means no caller has to know which models the
relationships happen to mention.
"""

from app.models.accounting import AccountingPeriod, PeriodState  # noqa: F401
from app.models.employee import Employee, EmploymentStatus  # noqa: F401
from app.models.invoicing import (  # noqa: F401
    Client,
    Invoice,
    InvoiceDirection,
    InvoiceItem,
    InvoiceProcessingStatus,
    InvoiceStatus,
    Supplier,
)
from app.models.leaves import (  # noqa: F401
    LeaveRequest,
    LeaveStatus,
    LeaveType,
)
from app.models.numbering import InvoiceSequence  # noqa: F401
from app.models.payroll import Payslip  # noqa: F401
from app.models.service import Service  # noqa: F401
from app.models.user import User  # noqa: F401
