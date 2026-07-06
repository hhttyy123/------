"""SQLAlchemy mappings for the first PostgreSQL import vertical slice."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(80))
    phone: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class StoredFile(Base):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    original_name: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    content_type: Mapped[str | None] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(String(64))
    uploaded_by: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    file_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("files.id"))
    module: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(30))
    mapping_version: Mapped[str | None] = mapped_column(String(50))
    total_rows: Mapped[int] = mapped_column(Integer)
    ready_rows: Mapped[int] = mapped_column(Integer)
    warning_rows: Mapped[int] = mapped_column(Integer)
    blocked_rows: Mapped[int] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(BigInteger)
    committed_by: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ImportRow(Base):
    __tablename__ = "import_rows"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    batch_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("import_batches.id"))
    sheet_name: Mapped[str] = mapped_column(String(160))
    source_row: Mapped[int] = mapped_column(Integer)
    source_region: Mapped[str] = mapped_column(String(80))
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSONB)
    normalized_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    record_fingerprint: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20))
    issues: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    target_table: Mapped[str | None] = mapped_column(String(80))
    target_record_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CashTransaction(Base):
    __tablename__ = "cash_transactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    transaction_date: Mapped[date] = mapped_column(Date)
    ledger_type: Mapped[str] = mapped_column(String(20))
    direction: Mapped[str] = mapped_column(String(10))
    category: Mapped[str] = mapped_column(String(40))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    payment_method: Mapped[str | None] = mapped_column(String(50))
    company_id: Mapped[int | None] = mapped_column(BigInteger)
    employee_id: Mapped[int | None] = mapped_column(BigInteger)
    summary: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20))
    reversal_of_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("cash_transactions.id"))
    source_import_row_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("import_rows.id"))
    created_by: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TransactionLink(Base):
    __tablename__ = "transaction_links"

    transaction_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cash_transactions.id"), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(40), primary_key=True)
    source_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    link_role: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    normalized_name: Mapped[str] = mapped_column(String(150), unique=True)
    contact_person: Mapped[str | None] = mapped_column(String(80))
    contact_phone: Mapped[str | None] = mapped_column(String(30))
    address: Mapped[str | None] = mapped_column(String(300))
    business_license_no: Mapped[str | None] = mapped_column(String(80))
    cooperation_status: Mapped[str] = mapped_column(String(20))
    cooperation_start_date: Mapped[date | None] = mapped_column(Date)
    cooperation_end_date: Mapped[date | None] = mapped_column(Date)
    default_receivable_days: Mapped[int | None] = mapped_column(Integer)
    remark: Mapped[str | None] = mapped_column(Text)
    source_import_row_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("import_rows.id"))
    version_no: Mapped[int] = mapped_column(Integer)
    created_by: Mapped[int | None] = mapped_column(BigInteger)
    updated_by: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.id"))
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    daily_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    required_count: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Employee(Base):
    __tablename__ = "employees"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(80)); id_card_encrypted: Mapped[str] = mapped_column(Text)
    id_card_hash: Mapped[str] = mapped_column(String(64), unique=True); id_card_last4: Mapped[str] = mapped_column(String(4))
    phone: Mapped[str | None] = mapped_column(String(30)); gender: Mapped[str | None] = mapped_column(String(10)); address: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(20)); source_import_row_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("import_rows.id")); version_no: Mapped[int] = mapped_column(Integer)
    created_by: Mapped[int | None] = mapped_column(BigInteger); updated_by: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True)); updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True)); deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EmploymentRecord(Base):
    __tablename__ = "employment_records"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True); employee_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("employees.id")); company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.id")); position_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("positions.id"))
    entry_date: Mapped[date] = mapped_column(Date); leave_date: Mapped[date | None] = mapped_column(Date); status: Mapped[str] = mapped_column(String(20)); remark: Mapped[str | None] = mapped_column(Text); source_import_row_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("import_rows.id")); created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True)); updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Contract(Base):
    __tablename__ = "contracts"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True); employee_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("employees.id")); company_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("companies.id")); contract_type: Mapped[str] = mapped_column(String(30)); contract_no: Mapped[str | None] = mapped_column(String(80)); sign_date: Mapped[date | None] = mapped_column(Date); start_date: Mapped[date] = mapped_column(Date); end_date: Mapped[date] = mapped_column(Date); status: Mapped[str] = mapped_column(String(20)); terminated_at: Mapped[date | None] = mapped_column(Date); remark: Mapped[str | None] = mapped_column(Text); source_import_row_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("import_rows.id")); created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True)); updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
