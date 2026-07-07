from datetime import date
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import get_db
from app.responses import excel_attachment_headers
from app.services.employee_db import create_contract,create_employee,employee_detail,expiring_contract_warnings,leave_employee,list_contracts,list_employees,terminate_contract,unsigned_contract_warnings,update_contract,update_employee
from io import BytesIO
from fastapi.responses import StreamingResponse
from openpyxl import Workbook

router=APIRouter()
class EmployeeWrite(BaseModel):
 name:str;id_card_number:str;phone:str;gender:str=Field(pattern='^(male|female)$');address:str|None=None;company_id:int;position_id:int|None=None;entry_date:date
class EmployeePatch(BaseModel):
 name:str|None=None;phone:str|None=None;gender:str|None=Field(default=None,pattern='^(male|female)$');address:str|None=None;company_id:int|None=None;position_id:int|None=None;entry_date:date|None=None
class ContractWrite(BaseModel):
 employee_id:int;company_id:int|None=None;contract_type:str='employee';contract_no:str|None=None;sign_date:date|None=None;start_date:date;end_date:date;remark:str|None=None
@router.get('')
def ls(search:str='',page:int=1,page_size:int=30,db:Session=Depends(get_db)):return list_employees(db,search,page,page_size)
@router.post('')
def add(p:EmployeeWrite,db:Session=Depends(get_db)):
 try:r=create_employee(db,p.model_dump());db.commit();return r
 except ValueError as e:db.rollback();raise HTTPException(400,str(e))
@router.patch('/{eid}')
def edit(eid:int,p:EmployeePatch,db:Session=Depends(get_db)):
 r=update_employee(db,eid,p.model_dump(exclude_unset=True))
 if not r:raise HTTPException(404,'人员不存在')
 return r
@router.post('/{eid}/leave')
def leave(eid:int,leave_date:date,db:Session=Depends(get_db)):
 if not leave_employee(db,eid,leave_date):raise HTTPException(404,'人员不存在')
 return {'ok':True}
@router.get('/{eid}/detail')
def detail(eid:int,db:Session=Depends(get_db)):
 r=employee_detail(db,eid)
 if not r:raise HTTPException(404,'人员不存在')
 return r
@router.get('/warnings/unsigned-contract')
def warns(db:Session=Depends(get_db)):return {'rows':unsigned_contract_warnings(db)}
@router.get('/contracts/list')
def contracts(employee_id:int|None=None,page:int=1,page_size:int=30,db:Session=Depends(get_db)):return list_contracts(db,employee_id,page,page_size)
@router.post('/contracts')
def contract_add(p:ContractWrite,db:Session=Depends(get_db)):return create_contract(db,p.model_dump())
@router.patch('/contracts/{cid}')
def contract_edit(cid:int,p:ContractWrite,db:Session=Depends(get_db)):
 r=update_contract(db,cid,p.model_dump(exclude_unset=True))
 if not r:raise HTTPException(404,'合同不存在')
 return r
@router.delete('/contracts/{cid}')
def contract_end(cid:int,db:Session=Depends(get_db)):
 if not terminate_contract(db,cid):raise HTTPException(404,'合同不存在')
 return {'ok':True}
@router.get('/warnings/contract-expiry')
def expiry(db:Session=Depends(get_db)):return {'rows':expiring_contract_warnings(db)}

@router.get('/export/file.xlsx')
def employees_export(db:Session=Depends(get_db)):
    from app.services.employee_db import _cipher
    data=list_employees(db,page_size=100000)
    wb=Workbook();ws=wb.active;ws.title="人员"
    ws.append(["姓名","身份证号","手机号","性别","企业","岗位","入职日期","状态"])
    cipher=_cipher()
    for r in data["rows"]:
        id_full=""
        try:
            emp=db.execute(text("SELECT id_card_encrypted FROM employees WHERE id=:eid"),{"eid":r["id"]}).scalar()
            if emp:id_full=cipher.decrypt(emp.encode()).decode()
        except:pass
        ws.append([r["name"],id_full or r["id_card_masked"],r["phone"],"男" if r["gender"]=="male" else "女",r["company_name"],r["position_name"],r["entry_date"],"在职" if r["status"]=="active" else "离职"])
    stream=BytesIO();wb.save(stream);stream.seek(0)
    return StreamingResponse(stream,media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",headers=excel_attachment_headers("人员花名册.xlsx"))

@router.get('/contracts/export/file.xlsx')
def contracts_export(db:Session=Depends(get_db)):
    from io import BytesIO; from openpyxl import Workbook; from fastapi.responses import StreamingResponse; from sqlalchemy import text
    rows=list_contracts(db,page_size=100000)['rows']; wb=Workbook(); ws=wb.active; ws.title="合同"
    ws.append(["员工","合同编号","合同类型","签订日期","起始日期","截止日期","状态"])
    for r in rows:
        emp=db.execute(text("SELECT name FROM employees WHERE id=:eid"),{"eid":r.get("employee_id")}).scalar()
        ws.append([emp or "",r.get("contract_no",""),r.get("contract_type",""),r.get("sign_date",""),r.get("start_date",""),r.get("end_date",""),r.get("status","")])
    stream=BytesIO(); wb.save(stream); stream.seek(0)
    return StreamingResponse(stream,media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",headers=excel_attachment_headers("合同列表.xlsx"))
