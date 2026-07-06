from datetime import date,timedelta
from app.services.employee_db import normalize_id,validate_employee_data
def test_employee_validation_rejects_bad_identity_phone_and_missing_company():
 issues=validate_employee_data({'name':'张三','id_card_number':'123','phone':'100','gender':'male','entry_date':date.today()})
 assert {x['field'] for x in issues}=={'id_card_number','phone','company_id'}
def test_normalize_identity_card_uppercases_x():assert normalize_id(' 32000000000000000x ')=='32000000000000000X'
