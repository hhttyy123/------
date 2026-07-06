import sys
sys.path.insert(0, ".")
# Simple test: remove Chinese and use only ASCII
with open("app/api/v2/advisor.py", "w", encoding="utf-8") as out:
    out.write("# advisor.py - ASCII only
")
    out.write("from fastapi import APIRouter, Depends
")
    out.write("from pydantic import BaseModel
")
    out.write("from datetime import date
")
    out.write("from sqlalchemy import text
")
    out.write("from sqlalchemy.orm import Session
")
    out.write("from app.agents.deepseek_client import get_client
")
    out.write("from app.config import settings
")
    out.write("from app.database import get_db
")
    out.write("
")
    out.write("router = APIRouter()
")
    out.write("client = get_client()
")
print("done")
