import os
import shutil
from datetime import datetime
from collections import defaultdict

from db import SessionLocal
from models import Issue


def get_size_format(b, factor=1024, suffix="B"):
    """Converts bytes to a human-readable format (e.g., 50.0GB)"""
    for unit in ["", "K", "M", "G", "T"]:
        if b < factor:
            return f"{b:.1f}{unit}{suffix}"
        b /= factor


def _extract_filename_from_url(url):
    """Extract filename from URL path like '/uploads/issue_20260324_xxx.jpg'"""
    if not url:
        return None
    return url.split('/')[-1] if '/' in url else url


def _get_file_size(upload_path, filename):
    """Get file size from uploads folder, returns 0 if file doesn't exist"""
    if not filename:
        return 0
    file_path = os.path.join(upload_path, filename)
    if os.path.exists(file_path):
        try:
            return os.path.getsize(file_path)
        except OSError:
            return 0
    return 0


def collect_maintenance_stats(upload_path="./uploads"):
    # 1. Get Global Disk Stats
    total, used, free = shutil.disk_usage("/")
    used_pct = (used / total) * 100

    # 2. Query Database for Issues
    daily_stats = defaultdict(lambda: {"issue_count": 0, "fix_count": 0, "size": 0})
    total_upload_size = 0

    # Track files linked to database records (to identify orphans later)
    linked_files = set()

    db = SessionLocal()
    try:
        # Query all issues from database
        issues = db.query(Issue).all()

        for issue in issues:
            # Extract date from issue's submitted_at timestamp
            if issue.submitted_at:
                date_str = issue.submitted_at.strftime("%Y%m%d")
            else:
                continue  # Skip issues without submission date

            # Process issue_photo
            if issue.issue_photo:
                filename = _extract_filename_from_url(issue.issue_photo)
                if filename:
                    linked_files.add(filename)
                    file_size = _get_file_size(upload_path, filename)
                    if file_size > 0:
                        daily_stats[date_str]["issue_count"] += 1
                        daily_stats[date_str]["size"] += file_size
                        total_upload_size += file_size

            # Process fix_photo (counted under the SAME issue date, not fix_date)
            if issue.fix_photo:
                filename = _extract_filename_from_url(issue.fix_photo)
                if filename:
                    linked_files.add(filename)
                    file_size = _get_file_size(upload_path, filename)
                    if file_size > 0:
                        daily_stats[date_str]["fix_count"] += 1
                        daily_stats[date_str]["size"] += file_size
                        total_upload_size += file_size

    finally:
        db.close()

    # 3. Orphan Check: Scan uploads folder for files NOT linked to database
    orphan_stats = {"file_count": 0, "size": 0}
    if os.path.exists(upload_path):
        for filename in os.listdir(upload_path):
            if filename.startswith(("issue_", "fix_")):
                if filename not in linked_files:
                    try:
                        file_path = os.path.join(upload_path, filename)
                        f_size = os.path.getsize(file_path)
                        orphan_stats["file_count"] += 1
                        orphan_stats["size"] += f_size
                    except (IndexError, OSError):
                        continue

    # 4. Calculate Prediction (based on database-linked uploads only)
    sorted_dates = sorted(daily_stats.keys())
    days_count = len(sorted_dates)

    predicted_days = 9999  # Default if no data
    if days_count > 0:
        avg_daily_growth = total_upload_size / days_count
        if avg_daily_growth > 0:
            predicted_days = int(free / avg_daily_growth)

    # 5. Format Table Data
    table_data = []
    for d in sorted_dates:
        table_data.append({
            "date": d,
            "issue_count": daily_stats[d]["issue_count"],
            "fix_count": daily_stats[d]["fix_count"],
            "size": get_size_format(daily_stats[d]["size"])
        })

    return {
        "summary": {
            "total": get_size_format(total),
            "used_pct": f"{used_pct:.1f}%",
            "days_left": predicted_days
        },
        "history": table_data,  # Contains date, issue_count, fix_count, size
        "orphan": {
            "file_count": orphan_stats["file_count"],
            "size": get_size_format(orphan_stats["size"])
        }
    }


if __name__ == "__main__":
    stats = collect_maintenance_stats()
    print(f"Total Disk: {stats['summary']['total']} | Usage: {stats['summary']['used_pct']} | Est. Survival: {stats['summary']['days_left']} days")
    print("-" * 30)
    print("Daily Detail (Latest 5):")
    for row in stats['history'][-5:]:
        print(f"Date: {row['date']} | Issue: {row['issue_count']} | Fix: {row['fix_count']} | Size: {row['size']}")
    print("-" * 30)
    print(f"Orphan Files: {stats['orphan']['file_count']} | Size: {stats['orphan']['size']}")
