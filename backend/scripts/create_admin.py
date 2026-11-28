r"""
Interactive CLI bootstrap script to securely create an initial ADMIN user.

Usage (from Smart-Retail-Inventory-Project/backend):
    .\.venv\Scripts\python.exe scripts/create_admin.py
"""

from __future__ import annotations

import getpass
import re
import sys
from pathlib import Path

# Ensure backend root is importable when invoked as `python scripts/create_admin.py`
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.database.session import SessionLocal
from app.models.user import User

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8


def create_admin_user(db: Session, name: str, email: str, password: str) -> User:
    """
    Validate inputs, reject duplicate emails, hash password, and create an ADMIN user
    inside an atomic SQLAlchemy transaction with rollback on failure.
    """
    clean_name = (name or "").strip()
    clean_email = (email or "").strip().lower()

    if len(clean_name) < 2:
        raise ValueError("Administrator name must be at least 2 characters.")
    if not clean_email or not EMAIL_REGEX.match(clean_email):
        raise ValueError("Please provide a valid email address.")
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")

    try:
        existing = db.query(User).filter(User.email == clean_email).first()
        if existing is not None:
            raise ValueError(f"A user with email '{clean_email}' already exists.")

        admin = User(
            name=clean_name,
            email=clean_email,
            password_hash=hash_password(password),
            role="ADMIN",
            location_id=None,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        return admin
    except Exception:
        db.rollback()
        raise


def main() -> int:
    print("=== StockSense Initial Administrator Bootstrap ===")
    try:
        name = input("Administrator full name: ").strip()
        email = input("Administrator email: ").strip()
        password = getpass.getpass("Administrator password (min 8 chars): ")
        confirm_password = getpass.getpass("Confirm password: ")
    except (KeyboardInterrupt, EOFError):
        print("\nAborted.")
        return 1

    if password != confirm_password:
        print("Error: Passwords do not match.", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        admin = create_admin_user(db, name=name, email=email, password=password)
        print(
            f"ADMIN account created successfully (user_id={admin.user_id}, email={admin.email}, role={admin.role})."
        )
        return 0
    except ValueError as exc:
        print(f"Validation error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Database error while creating administrator: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
