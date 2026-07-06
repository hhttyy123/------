from __future__ import annotations
import hashlib, re
from datetime import date, datetime, timedelta, timezone
from typing import Any
from cryptography.fernet import Fernet
from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session
from app.config import settings
from app.models import Company, Contract, Employee, EmploymentRecord, Position

ID_RE=re.compile(r"^\d{17}[\dX]$"); PHONE_RE=re.compile(r"^1\d{10}$")
def normalize_id(v:str)->str:return v.strip().upper().replace(' ','')
def validate_employee_data(data:dict[str,Any])->list[dict[str,str]]:
 issues=[]; ident=normalize_id(str(data.get('id_card_number') or '')); phone=re.sub(r'\D','',str(data.get('phone') or ''))
 if not data.get('name'):issues.append({'field':'name','message':'姓名不能为空'})
 if not ID_RE.fullmatch(ident):issues.append({'field':'id_card_number','message':'身份证号必须为18位'})
 if not PHONE_RE.fullmatch(phone):issues.append({'field':'phone','message':'手机号格式不正确'})
 if data.get('gender') not in ('male','female'):issues.append({'field':'gender','message':'性别必须为男或女'})
 if not data.get('entry_date'):issues.append({'field':'entry_date','message':'入职日期不能为空'})
 if not data.get('company_id'):issues.append({'field':'company_id','message':'未匹配到企业'})
 return issues
def _cipher():
 if not settings.DATA_ENCRYPTION_KEY:raise RuntimeError('DATA_ENCRYPTION_KEY 未配置')
 return Fernet(settings.DATA_ENCRYPTION_KEY.encode())
def create_employee(session:Session,data:dict[str,Any],source_import_row_id:int|None=None)->dict[str,Any]:
 issues=validate_employee_data(data)
 if issues:raise ValueError('；'.join(x['message'] for x in issues))
 ident=normalize_id(data['id_card_number']); digest=hashlib.sha256(ident.encode()).hexdigest()
 if session.scalar(select(Employee.id).where(Employee.id_card_hash==digest,Employee.deleted_at.is_(None))):raise ValueError('身份证号已存在')
 now=datetime.now(timezone.utc); emp=Employee(name=data['name'].strip(),id_card_encrypted=_cipher().encrypt(ident.encode()).decode(),id_card_hash=digest,id_card_last4=ident[-4:],phone=re.sub(r'\D','',data['phone']),gender=data['gender'],address=data.get('address') or None,status='active',source_import_row_id=source_import_row_id,version_no=1,created_by=None,updated_by=None,created_at=now,updated_at=now,deleted_at=None);session.add(emp);session.flush()
 work=EmploymentRecord(employee_id=emp.id,company_id=data['company_id'],position_id=data.get('position_id'),entry_date=data['entry_date'],leave_date=None,status='active',remark=None,source_import_row_id=source_import_row_id,created_at=now,updated_at=now);session.add(work);session.flush();return serialize_employee(emp,work,session)
def list_employees(session:Session,search:str='',page:int=1,page_size:int=30)->dict[str,Any]:
 conditions=[Employee.deleted_at.is_(None),EmploymentRecord.status=='active']
 if search:conditions.append(or_(Employee.name.ilike(f'%{search}%'),Employee.phone.ilike(f'%{search}%')))
 total=session.scalar(select(func.count()).select_from(Employee).join(EmploymentRecord,EmploymentRecord.employee_id==Employee.id).where(*conditions)) or 0
 rows=session.execute(select(Employee,EmploymentRecord).join(EmploymentRecord,EmploymentRecord.employee_id==Employee.id).where(*conditions).order_by(Employee.id.desc()).offset((page-1)*page_size).limit(page_size)).all()
 return {'rows':[serialize_employee(e,w,session) for e,w in rows],'total':total,'page':page,'page_size':page_size}
def update_employee(session:Session,eid:int,data:dict[str,Any])->dict[str,Any]|None:
 e=session.get(Employee,eid);w=session.scalar(select(EmploymentRecord).where(EmploymentRecord.employee_id==eid,EmploymentRecord.status=='active'))
 if not e or not w:return None
 for f in ('name','phone','gender','address'):
  if f in data:setattr(e,f,data[f])
 for f in ('company_id','position_id','entry_date'):
  if f in data:setattr(w,f,data[f])
 e.version_no+=1;e.updated_at=w.updated_at=datetime.now(timezone.utc);session.commit();return serialize_employee(e,w,session)
def leave_employee(session:Session,eid:int,leave_date:date)->bool:
 e=session.get(Employee,eid);w=session.scalar(select(EmploymentRecord).where(EmploymentRecord.employee_id==eid,EmploymentRecord.status=='active'))
 if not e or not w:return False
 e.status='inactive';w.status='left';w.leave_date=leave_date;e.updated_at=w.updated_at=datetime.now(timezone.utc);session.commit();return True
def unsigned_contract_warnings(session:Session,today:date|None=None)->list[dict[str,Any]]:
 today=today or date.today(); rows=session.execute(select(Employee,EmploymentRecord).join(EmploymentRecord,EmploymentRecord.employee_id==Employee.id).where(Employee.status=='active',EmploymentRecord.status=='active',EmploymentRecord.entry_date<today)).all();out=[]
 for e,w in rows:
  days=(today-w.entry_date).days
  if days>20 and not session.scalar(select(Contract.id).where(Contract.employee_id==e.id,Contract.status=='active')):out.append({'employee_id':e.id,'employee_name':e.name,'entry_date':w.entry_date.isoformat(),'days_worked':days,'type':'unsigned_contract'})
 return out
def list_contracts(session:Session,eid:int|None=None,page:int=1,page_size:int=30):
 conditions=[Contract.status!='terminated']
 if eid:conditions.append(Contract.employee_id==eid)
 total=session.scalar(select(func.count()).select_from(Contract).where(*conditions)) or 0
 rows=session.scalars(select(Contract).where(*conditions).order_by(Contract.id.desc()).offset((page-1)*page_size).limit(page_size)).all()
 return {'rows':[{'id':x.id,'employee_id':x.employee_id,'contract_type':x.contract_type,'contract_no':x.contract_no,'sign_date':x.sign_date.isoformat() if x.sign_date else None,'start_date':x.start_date.isoformat(),'end_date':x.end_date.isoformat(),'status':x.status,'remark':x.remark} for x in rows],'total':total,'page':page,'page_size':page_size}
def create_contract(session:Session,d:dict[str,Any]):
 now=datetime.now(timezone.utc);x=Contract(employee_id=d['employee_id'],company_id=d.get('company_id'),contract_type=d.get('contract_type','employee'),contract_no=d.get('contract_no'),sign_date=d.get('sign_date'),start_date=d['start_date'],end_date=d['end_date'],status='active',terminated_at=None,remark=d.get('remark'),source_import_row_id=None,created_at=now,updated_at=now);session.add(x);session.commit();return {'id':x.id}
def update_contract(session:Session,cid:int,d:dict[str,Any]):
 x=session.get(Contract,cid)
 if not x:return None
 for f in ('contract_type','contract_no','sign_date','start_date','end_date','remark','status'):
  if f in d:setattr(x,f,d[f])
 x.updated_at=datetime.now(timezone.utc);session.commit();return {'id':x.id}
def terminate_contract(session:Session,cid:int)->bool:
 x=session.get(Contract,cid)
 if not x:return False
 x.status='terminated';x.terminated_at=date.today();x.updated_at=datetime.now(timezone.utc);session.commit();return True
def expiring_contract_warnings(session:Session,today:date|None=None):
 today=today or date.today();rows=session.scalars(select(Contract).where(Contract.status=='active',Contract.end_date>=today,Contract.end_date<=today+timedelta(days=15))).all()
 names=dict(session.execute(select(Employee.id,Employee.name)).all());return [{'contract_id':x.id,'employee_id':x.employee_id,'employee_name':names.get(x.employee_id,''),'end_date':x.end_date.isoformat(),'days_left':(x.end_date-today).days,'type':'contract_expiry'} for x in rows]
def serialize_employee(e:Employee,w:EmploymentRecord,s:Session):
 c=s.get(Company,w.company_id);p=s.get(Position,w.position_id) if w.position_id else None
 return {'id':e.id,'name':e.name,'id_card_masked':f'**************{e.id_card_last4}','phone':e.phone,'gender':e.gender,'address':e.address,'status':e.status,'company_id':w.company_id,'company_name':c.name if c else '', 'position_id':w.position_id,'position_name':p.name if p else '', 'entry_date':w.entry_date.isoformat(),'contract_count':s.scalar(select(func.count()).select_from(Contract).where(Contract.employee_id==e.id)) or 0}

def employee_detail(session:Session,eid:int)->dict[str,Any]|None:
 e=session.get(Employee,eid);w=session.scalar(select(EmploymentRecord).where(EmploymentRecord.employee_id==eid).order_by(EmploymentRecord.id.desc()))
 if not e or not w:return None
 attendance=session.execute(text("""SELECT work_date,status,hours,deduction_amount,remark FROM attendance_records WHERE employment_id=:wid ORDER BY work_date DESC LIMIT 30"""),{'wid':w.id}).mappings().all()
 payroll=session.execute(text("""SELECT pb.salary_month,pb.pay_date,pb.status,pi.base_salary,pi.allowance,pi.deduction,pi.net_pay,pi.remark FROM payroll_items pi JOIN payroll_batches pb ON pb.id=pi.batch_id WHERE pi.employee_id=:eid ORDER BY pb.salary_month DESC LIMIT 24"""),{'eid':eid}).mappings().all()
 return {'employee':serialize_employee(e,w,session),'contracts':list_contracts(session,eid)['rows'],'attendance':[dict(x) for x in attendance],'payroll':[dict(x) for x in payroll]}
