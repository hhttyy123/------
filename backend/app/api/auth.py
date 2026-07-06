from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models import User
from app.services.auth import create_token, decode_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=10, max_length=128)


class BootstrapRequest(Credentials):
    display_name: str = Field(min_length=1, max_length=80)


def require_user(request: Request, authorization: str | None = Header(default=None), session_token: str | None = Cookie(default=None), db: Session = Depends(get_db)) -> User:
    token = authorization[7:] if authorization and authorization.startswith("Bearer ") else session_token
    if not token:
        raise HTTPException(401, "请先登录")
    try:
        payload = decode_token(token)
    except (ValueError, KeyError):
        raise HTTPException(401, "登录已失效")
    user = db.get(User, int(payload["sub"]))
    if not user or user.status != "active":
        raise HTTPException(401, "账号不可用")
    request.state.user_id = user.id
    return user


def user_role(db: Session, user_id: int) -> dict:
    row = db.execute(text("SELECT r.code,r.name,r.level FROM roles r JOIN user_roles ur ON ur.role_id=r.id WHERE ur.user_id=:uid ORDER BY r.level DESC LIMIT 1"), {"uid": user_id}).mappings().first()
    return dict(row) if row else {"code": "staff", "name": "一级员工", "level": 1}


def require_level(level: int):
    def dependency(user: User = Depends(require_user), db: Session = Depends(get_db)):
        if int(user_role(db, user.id)["level"]) < level: raise HTTPException(403, "权限不足")
        return user
    return dependency


@router.get("/status")
def status(db: Session = Depends(get_db)):
    return {"initialized": bool(db.scalar(select(func.count()).select_from(User)))}


@router.post("/bootstrap")
def bootstrap(payload: BootstrapRequest, response: Response, db: Session = Depends(get_db)):
    if db.scalar(select(func.count()).select_from(User)):
        raise HTTPException(409, "系统已经初始化")
    now = datetime.now(timezone.utc)
    user = User(username=payload.username.strip(), password_hash=hash_password(payload.password), display_name=payload.display_name.strip(), phone=None, status="active", last_login_at=now, created_at=now, updated_at=now)
    db.add(user); db.commit(); db.refresh(user)
    db.execute(text("INSERT INTO user_roles(user_id,role_id) SELECT :uid,id FROM roles WHERE code='admin' ON CONFLICT DO NOTHING"), {"uid": user.id}); db.commit()
    token = create_token(user.id, user.username)
    response.set_cookie("session_token", token, httponly=True, secure=settings.COOKIE_SECURE, samesite="strict", max_age=60*60*settings.AUTH_TOKEN_HOURS)
    return {"token": token, "user": {"id": user.id, "username": user.username, "display_name": user.display_name}}


@router.post("/login")
def login(payload: Credentials, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == payload.username.strip()))
    if not user or user.status != "active" or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "账号或密码错误")
    user.last_login_at = datetime.now(timezone.utc); db.commit()
    token = create_token(user.id, user.username)
    response.set_cookie("session_token", token, httponly=True, secure=settings.COOKIE_SECURE, samesite="strict", max_age=60*60*settings.AUTH_TOKEN_HOURS)
    return {"token": token, "user": {"id": user.id, "username": user.username, "display_name": user.display_name}}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("session_token")
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(require_user)):
    return {"id": user.id, "username": user.username, "display_name": user.display_name}


@router.get("/users")
def users(_: User = Depends(require_level(9)), db: Session = Depends(get_db)):
    rows=db.execute(text("SELECT u.id,u.username,u.display_name,u.status,COALESCE(r.code,'staff') role_code,COALESCE(r.name,'一级员工') role_name FROM users u LEFT JOIN user_roles ur ON ur.user_id=u.id LEFT JOIN roles r ON r.id=ur.role_id ORDER BY u.id")).mappings().all()
    return {"rows":[dict(x) for x in rows]}


class UserCreate(BootstrapRequest):
    role_code: str = Field(pattern="^(staff|finance|owner|admin)$")


@router.post("/users")
def create_user(payload: UserCreate, _: User = Depends(require_level(9)), db: Session = Depends(get_db)):
    if db.scalar(select(User.id).where(User.username==payload.username.strip())): raise HTTPException(409,"账号已存在")
    now=datetime.now(timezone.utc);user=User(username=payload.username.strip(),password_hash=hash_password(payload.password),display_name=payload.display_name.strip(),phone=None,status='active',last_login_at=None,created_at=now,updated_at=now);db.add(user);db.flush();db.execute(text("INSERT INTO user_roles(user_id,role_id) SELECT :uid,id FROM roles WHERE code=:role"),{'uid':user.id,'role':payload.role_code});db.commit();return {'id':user.id}


@router.patch("/users/{user_id}/role")
def change_role(user_id:int,role_code:str, _: User = Depends(require_level(9)),db:Session=Depends(get_db)):
    if role_code not in {'staff','finance','owner','admin'}:raise HTTPException(400,'角色无效')
    db.execute(text("DELETE FROM user_roles WHERE user_id=:uid"),{'uid':user_id});db.execute(text("INSERT INTO user_roles(user_id,role_id) SELECT :uid,id FROM roles WHERE code=:role"),{'uid':user_id,'role':role_code});db.commit();return {'ok':True}
