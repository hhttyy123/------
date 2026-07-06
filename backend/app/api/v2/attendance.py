from datetime import date, datetime, timezone
from decimal import Decimal

from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

router=APIRouter()

class AttendanceWrite(BaseModel):
    employee_id:int
    work_date:date
    status:str=Field(pattern='^(normal|late|absent|leave)$')
    hours:Decimal=Field(default=0,ge=0)
    deduction_amount:Decimal=Field(default=0,ge=0)
    remark:str|None=None

@router.get('')
def list_attendance(date_from:date|None=None,date_to:date|None=None,employee_id:int|None=None,db:Session=Depends(get_db)):
    conditions=[];params={}
    if date_from is not None:conditions.append('a.work_date>=:date_from');params['date_from']=date_from
    if date_to is not None:conditions.append('a.work_date<=:date_to');params['date_to']=date_to
    if employee_id is not None:conditions.append('e.id=:employee_id');params['employee_id']=employee_id
    where=(' WHERE '+' AND '.join(conditions)) if conditions else ''
    rows=db.execute(text('''SELECT a.id,e.id employee_id,e.name employee_name,a.work_date,a.status,a.hours,a.deduction_amount,a.remark FROM attendance_records a JOIN employment_records er ON er.id=a.employment_id JOIN employees e ON e.id=er.employee_id'''+where+' ORDER BY a.work_date DESC,a.id DESC LIMIT 1000'),params).mappings().all()
    return {'rows':[dict(x) for x in rows],'total':len(rows)}

def employment_id(db:Session,employee_id:int)->int:
    value=db.execute(text("SELECT id FROM employment_records WHERE employee_id=:eid AND status='active' ORDER BY id DESC LIMIT 1"),{'eid':employee_id}).scalar()
    if not value:raise HTTPException(400,'人员没有有效的在职记录')
    return value

@router.post('')
def create_attendance(p:AttendanceWrite,db:Session=Depends(get_db)):
    try:
        row=db.execute(text('''INSERT INTO attendance_records(employment_id,work_date,status,hours,deduction_amount,remark,created_at,updated_at) VALUES(:employment_id,:work_date,:status,:hours,:deduction_amount,:remark,:now,:now) RETURNING id'''),{**p.model_dump(),'employment_id':employment_id(db,p.employee_id),'now':datetime.now(timezone.utc)}).scalar_one();db.commit();return {'id':row}
    except Exception as e:
        db.rollback()
        if 'unique' in str(e).lower():raise HTTPException(409,'该人员当天考勤已存在')
        raise

@router.patch('/{record_id}')
def update_attendance(record_id:int,p:AttendanceWrite,db:Session=Depends(get_db)):
    result=db.execute(text('''UPDATE attendance_records SET employment_id=:employment_id,work_date=:work_date,status=:status,hours=:hours,deduction_amount=:deduction_amount,remark=:remark,updated_at=:now WHERE id=:id'''),{**p.model_dump(),'employment_id':employment_id(db,p.employee_id),'now':datetime.now(timezone.utc),'id':record_id});db.commit()
    if not result.rowcount:raise HTTPException(404,'考勤记录不存在')
    return {'ok':True}

@router.delete('/{record_id}')
def delete_attendance(record_id:int,db:Session=Depends(get_db)):
    result=db.execute(text('DELETE FROM attendance_records WHERE id=:id'),{'id':record_id});db.commit()
    if not result.rowcount:raise HTTPException(404,'考勤记录不存在')
    return {'ok':True}

@router.get('/export/file.xlsx')
def attendance_export(date_from:date|None=None,date_to:date|None=None,db:Session=Depends(get_db)):
    data=list_attendance(date_from=date_from,date_to=date_to,db=db)
    wb=Workbook();ws=wb.active;ws.title="考勤"
    ws.append(["日期","人员","状态","工时","扣款","备注"])
    for r in data["rows"]:
        ws.append([r["work_date"],r["employee_name"],r["status"],r["hours"],r["deduction_amount"],r["remark"] or ""])
    stream=BytesIO();wb.save(stream);stream.seek(0)
    return StreamingResponse(stream,media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",headers={"Content-Disposition":'attachment; filename="attendance.xlsx"'})
