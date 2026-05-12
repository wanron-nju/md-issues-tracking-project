#!/usr/bin/env python3
"""
Check date range and daily issue counts for a given owner.

Usage:
    python check_owner_dates.py <owner_name>

Example:
    python check_owner_dates.py 采购部
    python check_owner_dates.py 生鲜部
    python check_owner_dates.py 1001 - 明都店
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from models import Issue
from db import DATABASE_URL

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker


def main():
    parser = argparse.ArgumentParser(
        description="Check date range and daily issue counts for a given owner."
    )
    parser.add_argument(
        "owner",
        type=str,
        help="Issue owner name (e.g. 采购部, 生鲜部, or store name like '1001 - 明都店')",
    )
    args = parser.parse_args()

    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        owner = args.owner

        # Get date range
        min_date, max_date = db.query(
            func.date(func.min(Issue.submitted_at)),
            func.date(func.max(Issue.submitted_at)),
        ).filter(
            Issue.issue_owner == owner
        ).first()

        if min_date is None:
            print(f"No issues found for owner: {owner}")
            return

        # Get all dates with counts
        rows = (
            db.query(
                func.date(Issue.submitted_at).label("day"),
                func.count(Issue.id).label("cnt"),
            )
            .filter(Issue.issue_owner == owner)
            .group_by(func.date(Issue.submitted_at))
            .order_by(func.date(Issue.submitted_at))
            .all()
        )

        # Build a dict day -> count
        day_counts = {row.day: row.cnt for row in rows}

        # Convert min_date/max_date (strings) to date objects
        min_d = datetime.strptime(min_date, "%Y-%m-%d").date()
        max_d = datetime.strptime(max_date, "%Y-%m-%d").date()

        print(f"Owner: {owner}")
        print(f"Date range: {min_date} ~ {max_date}")
        print(f"Total issues: {sum(day_counts.values())}")
        print()
        print(f"{'日期':<12} {'问题数':>8}")
        print("-" * 22)

        # Iterate from min_date to max_date, print only days with issues
        current = min_d
        while current <= max_d:
            key = current.strftime("%Y-%m-%d")
            cnt = day_counts.get(key, 0)
            if cnt > 0:
                print(f"{key} {cnt:>8}")
            current += timedelta(days=1)

        print("-" * 22)

    finally:
        db.close()


if __name__ == "__main__":
    main()