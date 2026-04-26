#!/usr/bin/env python3
"""
Issue Statistics Script

Calculates issue statistics for a specified date window:
- Total issues created
- Number of resolved issues
- Issue resolve rate

Groups by issue owners (non-门店) and specific 门店.
Results are sorted by resolve rate DESC, with non-门店 owners first, then 门店.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

# Import models
import sys
sys.path.insert(0, str(Path(__file__).parent))
from models import Base, Issue
from db import DATABASE_URL

# Define the grouping order
NON_STORE_OWNERS = [
    '采购非食组',
    '采购农副组',
    '采购食品组',
    '品类组',
    '生鲜部（除水果组外）',
    '生鲜部（水果组）',
    '联营绿洁',
    '营运部',
    '财务部',
    '工程部',
    '企划部',
    '信息部',
    '人事部',
]

STORE_GROUPS = [
    '1001 - 明都店',
    '1010 - 魏村店',
    '1020 - 横林1店',
    '1021 - 百丈店',
    '1022 - 东安1店',
    '1028 - 魏村大顺发',
    '1035 - 雪堰2店',
    '1043 - 南都店',
    '1048 - 郑陆2店',
    '1050 - 湟里店',
    '1052 - 横林大顺发',
    '1056 - 潘家店',
    '1057 - 漕桥店',
    '1063 - 安家3店',
    '1068 - 邹区店',
    '1069 - 镇江店',
    '1077 - 礼河店',
    '1003 - 奔牛1店',
    '1005 - 奔牛2店',
    '1009 - 卜弋店',
    '1015 - 郑陆1店',
    '1016 - 村前店',
    '1042 - 农发区店',
    '1051 - 中天店',
    '1055 - 紫云店',
    '1058 - 学府店',
    '1059 - 怀德店',
    '1007 - 电力店',
    '1017 - 政务店',
    '1067 - 恒立店',
]


def get_stats(
    db_session,
    start_date: datetime,
    end_date: datetime,
    non_store_owners: list[str],
    store_groups: list[str],
) -> list[dict]:
    """
    Calculate issue statistics for each group within the date range.

    Args:
        db_session: SQLAlchemy database session
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        non_store_owners: List of non-门店 issue owner names
        store_groups: List of specific 门店 store names

    Returns:
        List of dictionaries containing stats for each group
    """
    # Get all issues within date range
    issues = db_session.query(Issue).filter(
        Issue.submitted_at >= start_date,
        Issue.submitted_at <= end_date
    ).all()

    # Initialize counters for each group
    stats = {}

    # Initialize non-store owners
    for owner in non_store_owners:
        stats[owner] = {'total': 0, 'resolved': 0}

    # Initialize store groups
    for store in store_groups:
        stats[store] = {'total': 0, 'resolved': 0}

    # Count issues for each group
    for issue in issues:
        if issue.issue_owner != '门店':
            # Non-门店 issue owner - group by issue_owner
            owner = issue.issue_owner
            if owner in stats:
                stats[owner]['total'] += 1
                if issue.status == 'completed':
                    stats[owner]['resolved'] += 1
        else:
            # 门店 issue - group by store name
            store = issue.store
            if store in stats:
                stats[store]['total'] += 1
                if issue.status == 'completed':
                    stats[store]['resolved'] += 1

    # Convert to list format with resolve rate
    results = []
    for group_name, counts in stats.items():
        total = counts['total']
        resolved = counts['resolved']
        resolve_rate = (resolved / total * 100) if total > 0 else 0.0
        results.append({
            'group': group_name,
            'total': total,
            'resolved': resolved,
            'unresolved': total - resolved,
            'resolve_rate': resolve_rate,
        })

    return results


def sort_and_print_stats(
    stats: list[dict],
    non_store_owners: list[str],
    store_groups: list[str],
) -> None:
    """
    Sort stats by resolve rate DESC, with non-门店 owners first, then 门店.
    """
    # Separate non-store and store stats
    non_store_stats = []
    store_stats = []

    for s in stats:
        if s['group'] in non_store_owners:
            non_store_stats.append(s)
        elif s['group'] in store_groups:
            store_stats.append(s)

    # Sort each by resolve rate DESC
    non_store_stats.sort(key=lambda x: x['resolve_rate'], reverse=True)
    store_stats.sort(key=lambda x: x['resolve_rate'], reverse=True)

    # Print header
    print("=" * 90)
    print(f"{'分组':<20} {'总问题数':>10} {'已整改':>10} {'待整改':>10} {'整改率':>12}")
    print("=" * 90)

    # Print non-门店 owners first
    for s in non_store_stats:
        print(f"{s['group']:<20} {s['total']:>10} {s['resolved']:>10} {s['unresolved']:>10} {s['resolve_rate']:>11.2f}%")

    # Separator between sections
    if non_store_stats and store_stats:
        print("-" * 90)

    # Print 门店 stores
    for s in store_stats:
        print(f"{s['group']:<20} {s['total']:>10} {s['resolved']:>10} {s['unresolved']:>10} {s['resolve_rate']:>11.2f}%")

    print("=" * 90)


def parse_date(date_str: str) -> datetime:
    """Parse date string in format YYYY-MM-DD to datetime."""
    return datetime.strptime(date_str, "%Y-%m-%d")


def main():
    parser = argparse.ArgumentParser(
        description="Calculate issue statistics for a specified date window."
    )
    parser.add_argument(
        "--start-date",
        type=str,
        required=True,
        help="Start date (YYYY-MM-DD format)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        required=True,
        help="End date (YYYY-MM-DD format)",
    )

    args = parser.parse_args()

    # Parse dates
    start_date = parse_date(args.start_date)
    # Set end_date to end of day (23:59:59)
    end_date = parse_date(args.end_date).replace(hour=23, minute=59, second=59)

    # Create database engine and session
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Calculate stats
        stats = get_stats(
            db,
            start_date,
            end_date,
            NON_STORE_OWNERS,
            STORE_GROUPS,
        )

        # Print summary header
        print(f"\n问题统计报告")
        print(f"日期范围: {args.start_date} 至 {args.end_date}")
        print(f"统计时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Sort and print
        sort_and_print_stats(stats, NON_STORE_OWNERS, STORE_GROUPS)

        # Print summary totals
        total_issues = sum(s['total'] for s in stats)
        total_resolved = sum(s['resolved'] for s in stats)
        overall_rate = (total_resolved / total_issues * 100) if total_issues > 0 else 0.0

        print(f"\n总计:")
        print(f"  总问题数: {total_issues}")
        print(f"  已整改: {total_resolved}")
        print(f"  待整改: {total_issues - total_resolved}")
        print(f"  整体整改率: {overall_rate:.2f}%")

    finally:
        db.close()


if __name__ == "__main__":
    main()

