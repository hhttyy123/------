from datetime import date,datetime,timezone
from decimal import Decimal
from typing import Any
from io import BytesIO
from pathlib import Path
from openpyxl import Workbook
import pandas as pd
from fastapi import APIRouter,Depends,HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel,Field,model_validator
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import get_db
from app.responses import excel_attachment_headers
from app.api.auth import require_user,user_role
from app.models import User
from app.config import settings

router=APIRouter(); now=lambda:datetime.now(timezone.utc)

class RebateWrite(BaseModel): company_id:int;employee_id:int|None=None;rebate_date:date;amount:Decimal=Field(gt=0);person_count:int=Field(default=1,gt=0);remark:str|None=None
class InvoiceWrite(BaseModel): company_id:int;invoice_no:str;invoice_date:date;amount:Decimal=Field(gt=0);remark:str|None=None
class ReceivableWrite(BaseModel): company_id:int;invoice_id:int|None=None;expected_date:date;amount:Decimal=Field(gt=0);received_amount:Decimal=Field(default=0,ge=0);remark:str|None=None
class PaymentWrite(BaseModel):
 company_id:int;payment_date:date;amount:Decimal=Field(gt=0);payment_method:str=Field(pattern='^(direct|bank_acceptance)$');acceptance_due_date:date|None=None;bank_reference:str|None=None;receivable_id:int|None=None;allocated_amount:Decimal|None=Field(default=None,gt=0);remark:str|None=None
 @model_validator(mode='after')
 def acceptance(self):
  if self.payment_method=='bank_acceptance' and not self.acceptance_due_date:raise ValueError('银行承兑必须填写到期日')
  return self
class SalaryWrite(BaseModel): employee_id:int;salary_month:date;pay_date:date|None=None;base_salary:Decimal=Field(ge=0);allowance:Decimal=Field(default=0,ge=0);deduction:Decimal=Field(default=0,ge=0);remark:str|None=None

def journal_link(db:Session,d:date,direction:str,category:str,amount:Decimal,source_type:str,source_id:int,company_id:int|None=None,employee_id:int|None=None,summary:str=''):
 tid=db.execute(text('''INSERT INTO cash_transactions(transaction_date,ledger_type,direction,category,amount,payment_method,company_id,employee_id,summary,status,created_at,updated_at) VALUES(:d,'bank',:direction,:category,:amount,NULL,:company,:employee,:summary,'confirmed',:now,:now) RETURNING id'''),{'d':d,'direction':direction,'category':category,'amount':amount,'company':company_id,'employee':employee_id,'summary':summary,'now':now()}).scalar_one();db.execute(text("INSERT INTO transaction_links(transaction_id,source_type,source_id,link_role,created_at) VALUES(:tid,:type,:sid,'origin',:now)"),{'tid':tid,'type':source_type,'sid':source_id,'now':now()});return tid

def void_link(db:Session,source_type:str,source_id:int):
 db.execute(text("UPDATE cash_transactions SET status='voided',updated_at=:now WHERE id IN (SELECT transaction_id FROM transaction_links WHERE source_type=:t AND source_id=:id)"),{'now':now(),'t':source_type,'id':source_id})

CFG={
 'rebate':('recruitment_rebates','r.id,r.company_id,c.name company_name,r.employee_id,e.name employee_name,r.rebate_date,r.amount,r.person_count,r.status,r.remark','r','LEFT JOIN companies c ON c.id=r.company_id LEFT JOIN employees e ON e.id=r.employee_id'),
 'invoice':('invoices','r.id,r.company_id,c.name company_name,r.invoice_no,r.invoice_date,r.amount,r.status,r.remark','r','JOIN companies c ON c.id=r.company_id'),
 'receivable':('receivables','r.id,r.company_id,c.name company_name,r.invoice_id,r.expected_date,r.amount,r.received_amount,r.status,r.remark','r','JOIN companies c ON c.id=r.company_id'),
 'payment':('payments','r.id,r.company_id,c.name company_name,r.payment_date,r.amount,r.payment_method,r.acceptance_due_date,r.bank_reference,r.status,r.remark','r','JOIN companies c ON c.id=r.company_id')}

@router.get('/{module}')
def listing(module:str,page:int=1,page_size:int=30,db:Session=Depends(get_db)):
 if module=='salary':
  base='FROM payroll_items pi JOIN payroll_batches pb ON pb.id=pi.batch_id JOIN employees e ON e.id=pi.employee_id JOIN companies c ON c.id=pi.company_id'
  total=db.execute(text(f'SELECT COUNT(*) {base}')).scalar() or 0
  rows=db.execute(text(f'SELECT pi.id,pb.id batch_id,e.id employee_id,e.name employee_name,c.name company_name,pb.salary_month,pb.pay_date,pb.status,pi.base_salary,pi.allowance,pi.deduction,pi.net_pay,pi.remark {base} ORDER BY pb.salary_month DESC,pi.id DESC LIMIT :limit OFFSET :offset'),{'limit':page_size,'offset':(page-1)*page_size}).mappings().all()
 elif module in CFG:
  table,cols,alias,joins=CFG[module];base=f'FROM {table} {alias} {joins}'
  total=db.execute(text(f'SELECT COUNT(*) {base}')).scalar() or 0
  rows=db.execute(text(f'SELECT {cols} {base} ORDER BY r.id DESC LIMIT :limit OFFSET :offset'),{'limit':page_size,'offset':(page-1)*page_size}).mappings().all()
 else:raise HTTPException(404,'模块不存在')
 return {'rows':[dict(x) for x in rows],'total':total,'page':page,'page_size':page_size}

@router.post('/rebate')
def rebate(p:RebateWrite,user:User=Depends(require_user),db:Session=Depends(get_db)):
 rid=db.execute(text('''INSERT INTO recruitment_rebates(company_id,employee_id,rebate_date,amount,person_count,status,remark,created_by,created_at,updated_at) VALUES(:company_id,:employee_id,:rebate_date,:amount,:person_count,'finance_review',:remark,:uid,:now,:now) RETURNING id'''),{**p.model_dump(),'uid':user.id,'now':now()}).scalar_one();db.commit();return {'id':rid}
@router.post('/invoice')
def invoice(p:InvoiceWrite,db:Session=Depends(get_db)):
 rid=db.execute(text('''INSERT INTO invoices(company_id,invoice_no,invoice_date,amount,status,remark,created_at,updated_at) VALUES(:company_id,:invoice_no,:invoice_date,:amount,'issued',:remark,:now,:now) RETURNING id'''),{**p.model_dump(),'now':now()}).scalar_one();db.commit();return {'id':rid}
@router.post('/receivable')
def receivable(p:ReceivableWrite,db:Session=Depends(get_db)):
 if p.received_amount>p.amount:raise HTTPException(400,'已收金额不能大于应收金额')
 status='paid' if p.received_amount==p.amount else 'partial' if p.received_amount else 'pending';rid=db.execute(text('''INSERT INTO receivables(company_id,invoice_id,expected_date,amount,received_amount,status,remark,created_at,updated_at) VALUES(:company_id,:invoice_id,:expected_date,:amount,:received_amount,:status,:remark,:now,:now) RETURNING id'''),{**p.model_dump(),'status':status,'now':now()}).scalar_one();db.commit();return {'id':rid}
@router.post('/payment')
def payment(p:PaymentWrite,db:Session=Depends(get_db)):
 data=p.model_dump(exclude={'receivable_id','allocated_amount'});rid=db.execute(text('''INSERT INTO payments(company_id,payment_date,amount,payment_method,acceptance_due_date,bank_reference,status,remark,created_at,updated_at) VALUES(:company_id,:payment_date,:amount,:payment_method,:acceptance_due_date,:bank_reference,'confirmed',:remark,:now,:now) RETURNING id'''),{**data,'now':now()}).scalar_one();journal_link(db,p.payment_date,'income','receivable',p.amount,'payment',rid,p.company_id,None,'企业回款')
 if p.receivable_id:
  allocated=p.allocated_amount or p.amount
  if allocated>p.amount:raise HTTPException(400,'分配金额不能大于回款金额')
  db.execute(text('INSERT INTO payment_allocations(payment_id,receivable_id,amount,created_at) VALUES(:p,:r,:a,:now)'),{'p':rid,'r':p.receivable_id,'a':allocated,'now':now()});db.execute(text("UPDATE receivables SET received_amount=received_amount+:a,status=CASE WHEN received_amount+:a>=amount THEN 'paid' ELSE 'partial' END,updated_at=:now WHERE id=:r AND received_amount+:a<=amount"),{'a':allocated,'r':p.receivable_id,'now':now()})
 db.commit();return {'id':rid}
@router.post('/salary')
def salary(p:SalaryWrite,user:User=Depends(require_user),db:Session=Depends(get_db)):
 work=db.execute(text("SELECT id,company_id FROM employment_records WHERE employee_id=:eid AND status='active' ORDER BY id DESC LIMIT 1"),{'eid':p.employee_id}).mappings().first()
 if not work:raise HTTPException(400,'人员没有有效在职记录')
 month=p.salary_month.replace(day=1);net=p.base_salary+p.allowance-p.deduction
 if net<0:raise HTTPException(400,'实发金额不能小于0')
 batch=db.execute(text("SELECT id FROM payroll_batches WHERE salary_month=:m AND name=:n"),{'m':month,'n':f'{month:%Y-%m}工资'}).scalar()
 if not batch:batch=db.execute(text("INSERT INTO payroll_batches(name,salary_month,pay_date,status,total_amount,rule_version,created_by,created_at,updated_at) VALUES(:n,:m,:p,'finance_review',0,'manual-v1',:u,:now,:now) RETURNING id"),{'n':f'{month:%Y-%m}工资','m':month,'p':p.pay_date,'u':user.id,'now':now()}).scalar_one()
 rid=db.execute(text('''INSERT INTO payroll_items(batch_id,employee_id,company_id,employment_id,base_salary,allowance,deduction,net_pay,remark,created_at,updated_at) VALUES(:b,:e,:c,:w,:base,:allowance,:deduction,:net,:remark,:now,:now) RETURNING id'''),{'b':batch,'e':p.employee_id,'c':work.company_id,'w':work.id,'base':p.base_salary,'allowance':p.allowance,'deduction':p.deduction,'net':net,'remark':p.remark,'now':now()}).scalar_one();db.execute(text('UPDATE payroll_batches SET total_amount=(SELECT COALESCE(SUM(net_pay),0) FROM payroll_items WHERE batch_id=:b),updated_at=:now WHERE id=:b'),{'b':batch,'now':now()});db.commit();return {'id':rid}

@router.post('/{module}/{record_id}/approve')
def approve(module:str,record_id:int,user:User=Depends(require_user),db:Session=Depends(get_db)):
 if module not in {'salary','rebate'}:raise HTTPException(404,'模块不支持审批')
 role=user_role(db,user.id);table='payroll_batches' if module=='salary' else 'recruitment_rebates';target='owner_review' if role['level']>=2 and role['level']<3 else 'confirmed' if role['level']>=3 else None
 if not target:raise HTTPException(403,'需要财务或老板权限')
 key=record_id
 if module=='salary':key=db.execute(text('SELECT batch_id FROM payroll_items WHERE id=:id'),{'id':record_id}).scalar() or record_id
 db.execute(text(f'UPDATE {table} SET status=:s,updated_at=:now WHERE id=:id'),{'s':target,'now':now(),'id':key})
 if target=='confirmed':
  if module=='rebate':
   r=db.execute(text('SELECT rebate_date,amount,company_id,employee_id FROM recruitment_rebates WHERE id=:id'),{'id':key}).mappings().one();journal_link(db,r.rebate_date,'expense','recruitment_rebate',r.amount,'rebate',key,r.company_id,r.employee_id,'代招返费')
  else:
   r=db.execute(text('SELECT pb.pay_date,pb.salary_month,pi.net_pay,pi.company_id,pi.employee_id FROM payroll_items pi JOIN payroll_batches pb ON pb.id=pi.batch_id WHERE pi.id=:id'),{'id':record_id}).mappings().one();journal_link(db,r.pay_date or r.salary_month,'expense','salary',r.net_pay,'payroll_item',record_id,r.company_id,r.employee_id,'工资发放')
 db.commit();return {'status':target}

MODEL={'rebate':RebateWrite,'invoice':InvoiceWrite,'receivable':ReceivableWrite,'payment':PaymentWrite,'salary':SalaryWrite}
@router.patch('/{module}/{record_id}')
def edit(module:str,record_id:int,payload:dict[str,Any],db:Session=Depends(get_db)):
 if module not in MODEL:raise HTTPException(404,'模块不存在')
 data=MODEL[module](**payload).model_dump();mapping={'rebate':('recruitment_rebates',['company_id','employee_id','rebate_date','amount','person_count','remark']),'invoice':('invoices',['company_id','invoice_no','invoice_date','amount','remark']),'receivable':('receivables',['company_id','invoice_id','expected_date','amount','received_amount','remark']),'payment':('payments',['company_id','payment_date','amount','payment_method','acceptance_due_date','bank_reference','remark'])}
 if module=='salary':
  net=data['base_salary']+data['allowance']-data['deduction'];db.execute(text('UPDATE payroll_items SET base_salary=:base_salary,allowance=:allowance,deduction=:deduction,net_pay=:net,remark=:remark,updated_at=:now WHERE id=:id'),{**data,'net':net,'now':now(),'id':record_id})
 else:
  table,fields=mapping[module];params={k:data.get(k) for k in fields};params.update(id=record_id,now=now());db.execute(text(f"UPDATE {table} SET "+','.join(f'{k}=:{k}' for k in fields)+",updated_at=:now WHERE id=:id"),params)
 db.commit();return {'ok':True}

@router.delete('/{module}/{record_id}')
def remove(module:str,record_id:int,db:Session=Depends(get_db)):
 table={'rebate':'recruitment_rebates','invoice':'invoices','receivable':'receivables','payment':'payments'}.get(module)
 if module=='salary':db.execute(text("UPDATE payroll_batches SET status='voided',updated_at=:now WHERE id=(SELECT batch_id FROM payroll_items WHERE id=:id)"),{'id':record_id,'now':now()});void_link(db,'payroll_item',record_id)
 elif table:db.execute(text(f"UPDATE {table} SET status='voided',updated_at=:now WHERE id=:id"),{'id':record_id,'now':now()});void_link(db,module,record_id)
 else:raise HTTPException(404,'模块不存在')
 db.commit();return {'ok':True}

FINANCE_EXPORT_LABELS={
 'salary':{'employee_name':'员工','company_name':'企业','salary_month':'工资月份','pay_date':'发薪日期','base_salary':'基本工资','allowance':'津贴','deduction':'扣款','net_pay':'实发金额','status':'状态','remark':'备注'},
 'rebate':{'company_name':'企业','employee_name':'关联员工','rebate_date':'返费日期','amount':'金额','person_count':'人数','status':'状态','remark':'备注'},
 'invoice':{'company_name':'企业','invoice_no':'发票编号','invoice_date':'开票日期','amount':'金额','status':'状态','remark':'备注'},
 'receivable':{'company_name':'企业','expected_date':'预计回款日','amount':'应收金额','received_amount':'已收金额','status':'状态','remark':'备注'},
 'payment':{'company_name':'企业','payment_date':'回款日期','amount':'金额','payment_method':'付款方式','acceptance_due_date':'承兑到期日','bank_reference':'银行流水','status':'状态','remark':'备注'},
}
MODULE_NAMES={'salary':'工资发放','rebate':'代招返费','invoice':'开票管理','receivable':'应收管理','payment':'回款管理'}

@router.get('/{module}/export')
def export(module:str,db:Session=Depends(get_db)):
 data=listing(module,page_size=100000,db=db);labels=FINANCE_EXPORT_LABELS.get(module,{})
 wb=Workbook();ws=wb.active;ws.title=MODULE_NAMES.get(module,module)
 if data['rows']:
  cols=[k for k in data['rows'][0] if not k.startswith('_') and k!='id' and k!='batch_id']
  ws.append([labels.get(c,c) for c in cols])
  for r in data['rows']:
   ws.append([r.get(c,'') for c in cols])
 stream=BytesIO();wb.save(stream);stream.seek(0)
 return StreamingResponse(stream,media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',headers=excel_attachment_headers(f'{MODULE_NAMES.get(module,module)}.xlsx'))

class ImportRequest(BaseModel):upload_id:str;sheet_name:str

# Column name aliases for finance import
FINANCE_ALIASES = {
    "salary": {
        "employee_name": {"员工姓名","姓名","员工","employee_name","name"},
        "salary_month": {"工资月份","月份","salary_month","month"},
        "pay_date": {"发薪日期","发放日期","pay_date","issued_at"},
        "base_salary": {"基本工资","base_salary"},
        "allowance": {"津贴","allowance"},
        "deduction": {"扣款","deduction"},
        "remark": {"备注","remark"},
    },
    "rebate": {
        "company_name": {"企业名称","企业","公司","company_name","company"},
        "employee_name": {"关联员工","员工姓名","姓名","employee_name"},
        "rebate_date": {"返费日期","日期","rebate_date","date"},
        "amount": {"金额","amount"},
        "person_count": {"涉及人数","人数","person_count","count"},
        "remark": {"备注","remark"},
    },
    "invoice": {
        "company_name": {"企业名称","企业","公司","company_name","company"},
        "invoice_no": {"发票号","发票编号","invoice_no","invoice_number"},
        "invoice_date": {"开票日期","日期","invoice_date","date"},
        "amount": {"金额","开票金额","amount"},
        "remark": {"备注","remark"},
    },
    "payment": {
        "company_name": {"企业名称","企业","公司","company_name","company"},
        "payment_date": {"回款日期","日期","payment_date","date"},
        "amount": {"金额","amount"},
        "payment_method": {"付款方式","payment_method","method"},
        "acceptance_due_date": {"承兑到期日","acceptance_due_date"},
        "bank_reference": {"银行流水","bank_reference"},
        "remark": {"备注","remark"},
    },
    "receivable": {
        "company_name": {"企业名称","企业","公司","company_name","company"},
        "expected_date": {"预计回款日期","预计日期","expected_date","due_date"},
        "amount": {"金额","应收金额","amount"},
        "received_amount": {"已收金额","received_amount"},
        "remark": {"备注","remark"},
    },
}

@router.post('/{module}/import')
def import_excel(module:str,p:ImportRequest,user:User=Depends(require_user),db:Session=Depends(get_db)):
    if module not in MODEL:raise HTTPException(404,'模块不存在')
    path=Path(settings.UPLOAD_DIR)/f'{p.upload_id}.xlsx'
    if not path.exists():raise HTTPException(404,'上传文件不存在')
    frame=pd.read_excel(path,sheet_name=p.sheet_name)
    # Build column mapping from aliases
    aliases = FINANCE_ALIASES.get(module, {})
    columns = {str(c).strip(): c for c in frame.columns}
    mapping = {}
    for field, names in aliases.items():
        for n in names:
            if n in columns:
                mapping[field] = columns[n]
                break
    # Get company/employee name -> id mapping if needed
    companies = {}
    employees = {}
    if "company_name" in aliases:
        companies = {c.name.strip(): c.id for c in db.execute(text("SELECT id, name FROM companies WHERE deleted_at IS NULL")).mappings().all()}
    if "employee_name" in aliases:
        employees = {e.name.strip(): e.id for e in db.execute(text("SELECT id, name FROM employees WHERE deleted_at IS NULL")).mappings().all()}
    count=0;errors=[]
    for i,row in frame.iterrows():
        try:
            raw = {str(k): (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
            data = {}
            for field, col in mapping.items():
                val = raw.get(col)
                if val is None or (isinstance(val, float) and pd.isna(val)):
                    data[field] = None
                else:
                    data[field] = val
            # Resolve names to IDs, remove name fields
            if "company_name" in mapping and mapping["company_name"] in raw:
                data["company_id"] = companies.get(str(raw.get(mapping["company_name"],"")).strip())
            if "employee_name" in mapping and mapping["employee_name"] in raw:
                data["employee_id"] = employees.get(str(raw.get(mapping["employee_name"],"")).strip())
            data.pop("company_name", None); data.pop("employee_name", None)
            # Convert month strings like "2026-02" to date
            for k in list(data.keys()):
                v = data.get(k)
                if k in ("salary_month",) and v and isinstance(v, str) and len(str(v)) == 7:
                    data[k] = str(v) + "-01"
                if k.endswith("_date") and v and isinstance(v, str) and len(str(v)) == 7:
                    data[k] = str(v) + "-01"
            # Convert Chinese enum values to English
            if data.get("payment_method") == "直接给付": data["payment_method"] = "direct"
            elif data.get("payment_method") == "银行承兑": data["payment_method"] = "bank_acceptance"
            obj=MODEL[module](**data)
            {'rebate':rebate,'invoice':invoice,'receivable':receivable,'payment':payment,'salary':salary}[module](obj,user,db) if module in {'rebate','salary'} else {'invoice':invoice,'receivable':receivable,'payment':payment}[module](obj,db);count+=1
        except Exception as e:db.rollback();errors.append({'row':int(i)+2,'error':str(e)})
    return {'imported_rows':count,'errors':errors}

@router.get('/profit/summary')
def profit(date_from:date,date_to:date,db:Session=Depends(get_db)):
 income=db.execute(text("SELECT COALESCE(SUM(amount),0) FROM cash_transactions WHERE direction='income' AND status='confirmed' AND transaction_date BETWEEN :a AND :b"),{'a':date_from,'b':date_to}).scalar()
 expense=db.execute(text("SELECT COALESCE(SUM(amount),0) FROM cash_transactions WHERE direction='expense' AND status='confirmed' AND transaction_date BETWEEN :a AND :b"),{'a':date_from,'b':date_to}).scalar()
 return {'income':float(income),'expense':float(expense),'net_profit':float(income-expense)}

@router.get('/profit/monthly')
def profit_monthly(date_from:date,date_to:date,db:Session=Depends(get_db)):
    rows=db.execute(text("""
        SELECT to_char(transaction_date,'YYYY-MM') AS month,
               COALESCE(SUM(amount) FILTER (WHERE direction='income'),0) AS income,
               COALESCE(SUM(amount) FILTER (WHERE direction='expense'),0) AS expense
        FROM cash_transactions WHERE status='confirmed'
          AND transaction_date BETWEEN :a AND :b
        GROUP BY month ORDER BY month
    """),{'a':date_from,'b':date_to}).mappings().all()
    items=[{'month':r['month'],'income':float(r['income']),'expense':float(r['expense']),'net_profit':round(float(r['income']-r['expense']),2)} for r in rows]
    total_income=sum(i['income'] for i in items)
    total_expense=sum(i['expense'] for i in items)
    return {'rows':items,'summary':{'total_income':round(total_income,2),'total_expense':round(total_expense,2),'net_profit':round(total_income-total_expense,2)}}
