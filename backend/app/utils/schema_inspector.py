"""
Supabase PostgreSQL Database Schema Inspector (Optimized Batch Mode)
Inspects the real PostgreSQL schema via PostgreSQL information_schema in efficient
batch queries and generates a comprehensive markdown report.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from collections import defaultdict

from sqlalchemy import text
from app.database.connection import get_engine, check_database_connection

EXPECTED_TABLES = [
    "LOCATIONS",
    "USERS",
    "SHOP_WAREHOUSE",
    "ALERTS",
    "PRODUCTS",
    "INVENTORY",
    "FORECASTS",
    "SALES",
    "SALE_ITEMS",
    "ORDERS",
    "ORDER_ITEMS",
    "DISPATCHES",
    "ORDER_ALLOCATIONS",
    "WORKER_TASKS",
    "DISPATCH_ITEMS",
    "STOCK_RESERVATIONS",
    "WORKER_TASK_ITEMS",
    "STOCK_TRANSFERS",
]


def inspect_schema(output_path: str | Path | None = None) -> Dict[str, Any]:
    """
    Perform deep inspection of the connected Supabase PostgreSQL schema.
    Uses batch queries against information_schema and pg_catalog.
    """
    report_lines: List[str] = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    report_lines.append("# Supabase PostgreSQL Database Schema Inspection Report\n")
    report_lines.append(f"**Generated at:** `{now}`  ")
    report_lines.append("**Inspection Engine:** SQLAlchemy 2.x + Psycopg 3 via PostgreSQL Information Schema  \n")

    # 1. Connection check
    conn_check = check_database_connection()
    if not conn_check.get("connected"):
        error_msg = conn_check.get("error", "Unknown connection failure")
        report_lines.append(f"> [!CAUTION]\n> **Database connection failed:** `{error_msg}`\n")
        report_lines.append("Cannot perform schema inspection. Please check DATABASE_URL credentials.")
        content = "\n".join(report_lines)
        if output_path:
            Path(output_path).write_text(content, encoding="utf-8")
        return {"connected": False, "error": error_msg, "report": content}

    report_lines.append(
        f"> [!NOTE]\n"
        f"> **Database Connection Verified:** Connected via `{conn_check.get('driver')}` dialect in {conn_check.get('latency_ms')}ms.\n"
    )

    engine = get_engine()
    with engine.connect() as conn:
        # 1. Get all columns
        col_rows = conn.execute(text("""
            SELECT table_name, column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position;
        """)).fetchall()

        # 2. Get all Primary Keys
        pk_rows = conn.execute(text("""
            SELECT tc.table_name, kcu.column_name, tc.constraint_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY'
              AND tc.table_schema = 'public'
            ORDER BY tc.table_name, kcu.ordinal_position;
        """)).fetchall()

        # 3. Get all Foreign Keys
        fk_rows = conn.execute(text("""
            SELECT
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name,
                tc.constraint_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
              AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
              AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = 'public'
            ORDER BY tc.table_name, kcu.column_name;
        """)).fetchall()

        # 4. Get all Unique Constraints
        uq_rows = conn.execute(text("""
            SELECT tc.table_name, kcu.column_name, tc.constraint_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'UNIQUE'
              AND tc.table_schema = 'public'
            ORDER BY tc.table_name, tc.constraint_name;
        """)).fetchall()

        # 5. Get all Check Constraints
        ck_rows = conn.execute(text("""
            SELECT tc.table_name, tc.constraint_name, cc.check_clause
            FROM information_schema.table_constraints tc
            JOIN information_schema.check_constraints cc
              ON tc.constraint_name = cc.constraint_name
             AND tc.constraint_schema = cc.constraint_schema
            WHERE tc.constraint_type = 'CHECK'
              AND tc.table_schema = 'public'
            ORDER BY tc.table_name, tc.constraint_name;
        """)).fetchall()

        # 6. Get all Indexes
        idx_rows = conn.execute(text("""
            SELECT tablename, indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname;
        """)).fetchall()

    # Structure data by table
    table_columns = defaultdict(list)
    for r in col_rows:
        table_columns[r[0]].append({
            "name": r[1],
            "type": r[2],
            "nullable": r[3],
            "default": r[4],
        })

    table_pks = defaultdict(list)
    for r in pk_rows:
        table_pks[r[0]].append(r[1])

    table_fks = defaultdict(list)
    for r in fk_rows:
        table_fks[r[0]].append({
            "column": r[1],
            "foreign_table": r[2],
            "foreign_column": r[3],
            "constraint_name": r[4],
        })

    table_uqs = defaultdict(lambda: defaultdict(list))
    for r in uq_rows:
        table_uqs[r[0]][r[2]].append(r[1])

    table_cks = defaultdict(list)
    for r in ck_rows:
        table_cks[r[0]].append({"name": r[1], "clause": r[2]})

    table_idxs = defaultdict(list)
    for r in idx_rows:
        table_idxs[r[0]].append({"name": r[1], "def": r[2]})

    table_names = sorted(list(table_columns.keys()))

    report_lines.append("## 1. Discovered Tables Summary\n")
    report_lines.append(f"- **Total Tables Discovered:** `{len(table_names)}`")
    report_lines.append(f"- **Total Columns Across All Tables:** `{len(col_rows)}`")
    report_lines.append(f"- **Total Foreign Key Relationships:** `{len(fk_rows)}`\n")

    # Checklist comparison
    lower_discovered = {t.lower(): t for t in table_names}
    report_lines.append("### Table Verification Checklist\n")
    report_lines.append("| Expected Table Name | Discovered in Database | Actual Case in DB | Status |")
    report_lines.append("|---|---|---|---|")

    matched_count = 0
    for exp in EXPECTED_TABLES:
        exp_lower = exp.lower()
        if exp_lower in lower_discovered:
            actual = lower_discovered[exp_lower]
            matched_count += 1
            status = "FOUND"
        else:
            actual = "—"
            status = "MISSING"
        report_lines.append(f"| `{exp}` | `{'Yes' if status == 'FOUND' else 'No'}` | `{actual}` | {status} |")

    report_lines.append(f"\n**Matches:** `{matched_count} / {len(EXPECTED_TABLES)}` expected tables found.\n")

    # Table Details
    report_lines.append("## 2. Table-by-Table Specifications\n")

    for table in table_names:
        report_lines.append(f"### Table: `{table}`\n")

        pks = set(table_pks.get(table, []))
        columns = table_columns[table]

        # Columns table
        report_lines.append("| Column Name | Data Type | Nullable | Default | PK |")
        report_lines.append("|---|---|---|---|---|")
        for col in columns:
            name = col["name"]
            col_type = col["type"]
            nullable = col["nullable"]
            default = str(col["default"]) if col.get("default") is not None else "None"
            is_pk = "PK" if name in pks else ""
            report_lines.append(f"| `{name}` | `{col_type}` | `{nullable}` | `{default}` | {is_pk} |")
        report_lines.append("")

        # Primary Key
        if pks:
            report_lines.append(f"- **Primary Key:** `{', '.join(sorted(list(pks)))}`")

        # Foreign Keys
        fks = table_fks.get(table, [])
        if fks:
            report_lines.append("- **Foreign Keys:**")
            for fk in fks:
                report_lines.append(
                    f"  - `{fk['column']}` -> `{fk['foreign_table']}({fk['foreign_column']})` (Constraint: `{fk['constraint_name']}`)"
                )
        else:
            report_lines.append("- **Foreign Keys:** None")

        # Unique Constraints
        uqs = table_uqs.get(table, {})
        if uqs:
            report_lines.append("- **Unique Constraints:**")
            for uq_name, uq_cols in uqs.items():
                report_lines.append(f"  - `{', '.join(uq_cols)}` (Name: `{uq_name}`)")

        # Check Constraints
        cks = table_cks.get(table, [])
        if cks:
            report_lines.append("- **Check Constraints:**")
            for ck in cks:
                report_lines.append(f"  - `{ck['name']}`: `{ck['clause']}`")

        # Indexes
        idxs = table_idxs.get(table, [])
        if idxs:
            report_lines.append("- **Indexes:**")
            for idx in idxs:
                report_lines.append(f"  - `{idx['name']}`: `{idx['def']}`")

        report_lines.append("\n---\n")

    content = "\n".join(report_lines)

    if output_path:
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(content, encoding="utf-8")
        print(f"Schema inspection report saved to {out_file.resolve()}")

    return {
        "connected": True,
        "table_count": len(table_names),
        "tables": table_names,
        "matched_expected_count": matched_count,
        "total_columns": len(col_rows),
        "total_foreign_keys": len(fk_rows),
    }


if __name__ == "__main__":
    report_file = Path(__file__).resolve().parents[2] / "SCHEMA_INSPECTION.md"
    res = inspect_schema(report_file)
    if res.get("connected"):
        print(f"SUCCESS: Discovered {res.get('table_count')} tables, {res.get('total_columns')} columns, {res.get('total_foreign_keys')} foreign keys.")
        sys.exit(0)
    else:
        print(f"FAILED: {res.get('error')}")
        sys.exit(1)
