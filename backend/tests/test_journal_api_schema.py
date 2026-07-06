import pytest
from pydantic import ValidationError

from app.api.v2.journal import JournalPatch, JournalWrite


def test_journal_write_rejects_non_positive_amount():
    with pytest.raises(ValidationError):
        JournalWrite(
            transaction_date="2026-01-01",
            ledger_type="cash",
            direction="income",
            amount=0,
        )


def test_journal_patch_requires_a_field():
    with pytest.raises(ValidationError):
        JournalPatch()
