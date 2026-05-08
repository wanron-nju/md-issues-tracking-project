#!/usr/bin/env python3
"""
Manual Issue Deletion Script

Deletes a specific issue entry from the database and removes associated photo files.

Usage:
    python delete_issue.py <issue_id>

Example:
    python delete_issue.py 123

This will:
1. Look up the issue in the database
2. Display the issue details for confirmation
3. Delete the issue photo file (if exists)
4. Delete the fix photo file (if exists)
5. Remove the database entry

Requires:
    - SQLite database at ./data/issues.db
    - Uploads directory with photo files
"""

import sys
import os
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from db import engine, DB_PATH, DATA_DIR
from models import Base, Issue
from sqlalchemy.orm import Session


def delete_issue_by_id(issue_id: int, dry_run: bool = False):
    """
    Delete an issue by its ID.
    
    Args:
        issue_id: The ID of the issue to delete
        dry_run: If True, only show what would be deleted without actually deleting
    
    Returns:
        True if deletion was successful, False otherwise
    """
    uploads_dir = Path(__file__).parent / "uploads"
    
    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        return False
    
    if not uploads_dir.exists():
        print(f"WARNING: Uploads directory not found at {uploads_dir}")
    
    # Create database session
    db = Session(bind=engine)
    
    try:
        # Find the issue
        issue = db.query(Issue).filter(Issue.id == issue_id).first()
        
        if not issue:
            print(f"ERROR: Issue with ID {issue_id} not found in database.")
            return False
        
        # Display issue details
        print("=" * 60)
        print("ISSUE DETAILS")
        print("=" * 60)
        print(f"ID:              {issue.id}")
        print(f"Submitted At:    {issue.submitted_at}")
        print(f"Store:           {issue.store}")
        print(f"Content:         {issue.content[:80]}{'...' if len(issue.content) > 80 else ''}")
        print(f"Issue Owner:     {issue.issue_owner}")
        print(f"Store Sector:    {issue.store_sector or '(none)'}")
        print(f"Status:          {issue.status}")
        print(f"Issue Photo:     {issue.issue_photo or '(none)'}")
        print(f"Fix Photo:       {issue.fix_photo or '(none)'}")
        print(f"Fix Comments:    {(issue.fix_comments or '')[:50]}{'...' if issue.fix_comments and len(issue.fix_comments) > 50 else ''}")
        print(f"Fix Date:        {issue.fix_date or '(none)'}")
        print("=" * 60)
        
        # Collect files to delete
        files_to_delete = []
        
        if issue.issue_photo:
            filename = issue.issue_photo.split('/')[-1]
            file_path = uploads_dir / filename
            if file_path.exists():
                files_to_delete.append(("Issue Photo", file_path))
            else:
                print(f"WARNING: Issue photo file not found: {file_path}")
        
        if issue.fix_photo:
            filename = issue.fix_photo.split('/')[-1]
            file_path = uploads_dir / filename
            if file_path.exists():
                files_to_delete.append(("Fix Photo", file_path))
            else:
                print(f"WARNING: Fix photo file not found: {file_path}")
        
        # Display files that will be deleted
        if files_to_delete:
            print("\nFILES TO DELETE:")
            for desc, path in files_to_delete:
                print(f"  - {desc}: {path}")
        else:
            print("\nNo photo files to delete.")
        
        print("=" * 60)
        
        if dry_run:
            print("DRY RUN MODE - No changes were made.")
            return True
        
        # Ask for confirmation
        print(f"\nThis will DELETE the issue #{issue_id} and {len(files_to_delete)} file(s).")
        response = input("Are you sure you want to proceed? (yes/no): ").strip().lower()
        
        if response != 'yes':
            print("Deletion cancelled.")
            return False
        
        # Delete files
        print("\nDeleting files...")
        for desc, file_path in files_to_delete:
            try:
                file_path.unlink()
                print(f"  DELETED: {file_path}")
            except Exception as e:
                print(f"  ERROR deleting {file_path}: {e}")
        
        # Delete database entry
        print("\nDeleting database entry...")
        db.delete(issue)
        db.commit()
        print(f"  DELETED: Issue #{issue_id} from database")
        
        print("\n" + "=" * 60)
        print("SUCCESS: Issue and associated files have been deleted.")
        print("=" * 60)
        return True
        
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        return False
    finally:
        db.close()


def main():
    # Check arguments
    if len(sys.argv) < 2:
        print("Usage: python delete_issue.py <issue_id> [--dry-run]")
        print("")
        print("Arguments:")
        print("  issue_id    The ID of the issue to delete (required)")
        print("  --dry-run   Show what would be deleted without actually deleting")
        print("")
        print("Example:")
        print("  python delete_issue.py 123")
        print("  python delete_issue.py 123 --dry-run")
        sys.exit(1)
    
    # Parse arguments
    issue_id_str = sys.argv[1]
    dry_run = "--dry-run" in sys.argv
    
    # Validate issue_id
    try:
        issue_id = int(issue_id_str)
    except ValueError:
        print(f"ERROR: '{issue_id_str}' is not a valid integer.")
        sys.exit(1)
    
    if issue_id <= 0:
        print(f"ERROR: Issue ID must be a positive integer.")
        sys.exit(1)
    
    # Run deletion
    if dry_run:
        print("DRY RUN MODE - Showing what would be deleted...")
        print("")
    
    success = delete_issue_by_id(issue_id, dry_run=dry_run)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
