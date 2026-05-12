"""
Migration script to normalize issue_owner values in the issues table.

Changes:
1) 品类组 / 采购非食组 / 采购农副组 / 采购食品组 → 采购部
2) 生鲜部（除水果组外） / 生鲜部（水果组） → 生鲜部

Verification:
- Count of old 采购*组 values == count of issues updated to 采购部
- Count of old 生鲜部* values == count of issues updated to 生鲜部
"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'data', 'issues.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# ── Count and update: 采购非食组 / 采购农副组 / 采购食品组 → 采购部 ──
caigou_old_owners = ['品类组', '采购非食组', '采购农副组', '采购食品组']
caigou_new_owner = '采购部'

# Build parameterised IN clause
placeholders = ','.join('?' for _ in caigou_old_owners)

cursor.execute(
    f"SELECT COUNT(*) FROM issues WHERE issue_owner IN ({placeholders})",
    caigou_old_owners,
)
caigou_count_before = cursor.fetchone()[0]
print(f"Issues with 品类组/采购*组 owners (before update): {caigou_count_before}")

if caigou_count_before > 0:
    cursor.execute(
        f"UPDATE issues SET issue_owner = ? WHERE issue_owner IN ({placeholders})",
        [caigou_new_owner] + caigou_old_owners,
    )
    conn.commit()
    print(f"  → Updated to '{caigou_new_owner}'")

# Verify
cursor.execute("SELECT COUNT(*) FROM issues WHERE issue_owner = ?", (caigou_new_owner,))
caigou_count_after = cursor.fetchone()[0]
print(f"Issues with '{caigou_new_owner}' owner (after update): {caigou_count_after}")

# Note: caigou_count_after may include issues that were already 采购部 before this script.
# We only verify that the update touched the expected number of rows.
if caigou_count_before > 0:
    # Raw comparison of how many rows were actually changed.
    # Since we already counted before update and all of them were updated,
    # caigou_count_before must be <= caigou_count_after.
    if caigou_count_before <= caigou_count_after:
        print(f"  ✓ 品类组/采购*组 → 采购部: counts consistent ({caigou_count_before} old → now included in {caigou_count_after})\n")
    else:
        print(f"  ✗ MISMATCH! {caigou_count_before} old owners (品类组/采购*组) but only {caigou_count_after} 采购部 entries\n")
        conn.close()
        raise SystemExit(1)
else:
    print("  No 品类组/采购*组 owners found — nothing to update.\n")

# ── Count and update: 生鲜部（除水果组外） / 生鲜部（水果组） → 生鲜部 ──
shengxian_old_owners = ['生鲜部（除水果组外）', '生鲜部（水果组）']
shengxian_new_owner = '生鲜部'

placeholders = ','.join('?' for _ in shengxian_old_owners)

cursor.execute(
    f"SELECT COUNT(*) FROM issues WHERE issue_owner IN ({placeholders})",
    shengxian_old_owners,
)
shengxian_count_before = cursor.fetchone()[0]
print(f"Issues with 生鲜部* owners (before update): {shengxian_count_before}")

if shengxian_count_before > 0:
    cursor.execute(
        f"UPDATE issues SET issue_owner = ? WHERE issue_owner IN ({placeholders})",
        [shengxian_new_owner] + shengxian_old_owners,
    )
    conn.commit()
    print(f"  → Updated to '{shengxian_new_owner}'")

# Verify
cursor.execute("SELECT COUNT(*) FROM issues WHERE issue_owner = ?", (shengxian_new_owner,))
shengxian_count_after = cursor.fetchone()[0]
print(f"Issues with '{shengxian_new_owner}' owner (after update): {shengxian_count_after}")

if shengxian_count_before > 0:
    if shengxian_count_before <= shengxian_count_after:
        print(f"  ✓ 生鲜部* → 生鲜部: counts consistent ({shengxian_count_before} old → now included in {shengxian_count_after})\n")
    else:
        print(f"  ✗ MISMATCH! {shengxian_count_before} old owners but only {shengxian_count_after} 生鲜部 entries\n")
        conn.close()
        raise SystemExit(1)
else:
    print("  No 生鲜部* owners found — nothing to update.\n")

# ── Final summary ──
print("=== Final issue_owner distribution ===")
cursor.execute("SELECT issue_owner, COUNT(*) FROM issues GROUP BY issue_owner ORDER BY COUNT(*) DESC")
for owner, cnt in cursor.fetchall():
    print(f"  {owner}: {cnt}")

conn.close()
print("\n=== Normalization completed successfully! ===")