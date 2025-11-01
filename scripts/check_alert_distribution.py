"""
Check Alert Distribution

Shows how alerts are distributed across teams and types.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Alert
from collections import Counter
from datetime import datetime, timedelta

db = SessionLocal()

# Get all alerts
all_alerts = db.query(Alert).all()

# Get recent alerts (last 24 hours)
recent_cutoff = datetime.utcnow() - timedelta(hours=24)
recent_alerts = [a for a in all_alerts if a.created_at >= recent_cutoff]

print("="*70)
print("ALERT DISTRIBUTION REPORT")
print("="*70)

print(f"\nTotal Alerts: {len(all_alerts)}")
print(f"Recent Alerts (24h): {len(recent_alerts)}")

if not all_alerts:
    print("\n⚠️  No alerts found in database")
    print("\nTo generate alerts:")
    print("  1. python scripts/test_diverse_alerts.py")
    print("  2. Wait 30-60 seconds for processing")
    print("  3. Run this script again")
    exit(0)

# Analyze all alerts
print("\n" + "="*70)
print("ALL ALERTS")
print("="*70)

roles = Counter([a.role.value for a in all_alerts])
types = Counter([a.alert_type for a in all_alerts])
severities = Counter([a.severity.value for a in all_alerts])

print("\n📊 Distribution by Team Role:")
role_icons = {"front": "🧭", "compliance": "🕵️‍♀️", "legal": "⚖️"}
for role, count in sorted(roles.items(), key=lambda x: -x[1]):
    icon = role_icons.get(role, "•")
    pct = (count / len(all_alerts)) * 100
    print(f"  {icon} {role.upper():12s}: {count:3d} alerts ({pct:5.1f}%)")

print("\n📋 Distribution by Alert Type:")
for alert_type, count in sorted(types.items(), key=lambda x: -x[1]):
    pct = (count / len(all_alerts)) * 100
    print(f"  • {alert_type:30s}: {count:3d} alerts ({pct:5.1f}%)")

print("\n🚨 Distribution by Severity:")
severity_icons = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}
for severity, count in sorted(severities.items(), key=lambda x: ["low", "medium", "high", "critical"].index(x[0])):
    icon = severity_icons.get(severity, "•")
    pct = (count / len(all_alerts)) * 100
    print(f"  {icon} {severity.upper():12s}: {count:3d} alerts ({pct:5.1f}%)")

# Show recent alerts if different
if recent_alerts and len(recent_alerts) < len(all_alerts):
    print("\n" + "="*70)
    print("RECENT ALERTS (Last 24 Hours)")
    print("="*70)
    
    recent_roles = Counter([a.role.value for a in recent_alerts])
    recent_types = Counter([a.alert_type for a in recent_alerts])
    
    print(f"\nTotal Recent: {len(recent_alerts)}")
    
    print("\n📊 Distribution by Team Role:")
    for role, count in sorted(recent_roles.items(), key=lambda x: -x[1]):
        icon = role_icons.get(role, "•")
        pct = (count / len(recent_alerts)) * 100
        print(f"  {icon} {role.upper():12s}: {count:3d} alerts ({pct:5.1f}%)")
    
    print("\n📋 Distribution by Alert Type:")
    for alert_type, count in sorted(recent_types.items(), key=lambda x: -x[1]):
        pct = (count / len(recent_alerts)) * 100
        print(f"  • {alert_type:30s}: {count:3d} alerts ({pct:5.1f}%)")

# Show sample alerts for each team
print("\n" + "="*70)
print("SAMPLE ALERTS BY TEAM")
print("="*70)

for role_name in ["legal", "compliance", "front"]:
    role_alerts = [a for a in all_alerts if a.role.value == role_name]
    if role_alerts:
        print(f"\n{role_icons.get(role_name, '•')} {role_name.upper()} Team ({len(role_alerts)} alerts):")
        
        # Show up to 3 examples
        for alert in role_alerts[:3]:
            print(f"\n  Alert ID: {alert.alert_id}")
            print(f"  Type: {alert.alert_type}")
            print(f"  Severity: {alert.severity.value}")
            print(f"  Title: {alert.title}")
            print(f"  Created: {alert.created_at}")

print("\n" + "="*70)
print("DIVERSITY CHECK")
print("="*70)

# Check if alerts are diverse
unique_teams = len(roles)
unique_types = len(types)

print(f"\n✓ Unique Teams: {unique_teams}/3 (Legal, Compliance, Front)")
print(f"✓ Unique Alert Types: {unique_types}")

if unique_teams == 1:
    print("\n⚠️  WARNING: All alerts going to same team!")
    print("   This suggests insufficient diversity in transaction data.")
    print("\n   Recommendations:")
    print("   1. Run: python scripts/test_diverse_alerts.py")
    print("   2. Ensure transactions have varied characteristics:")
    print("      - Different countries (especially high-risk)")
    print("      - Different amounts (structuring range, high-value)")
    print("      - Missing vs complete documentation")
elif unique_teams == 2:
    print("\n⚠️  WARNING: Only 2 teams receiving alerts")
    print("   Consider adding more diverse transaction scenarios.")
else:
    print("\n✅ GOOD: Alerts distributed across all 3 teams")

if unique_types <= 2:
    print(f"\n⚠️  WARNING: Only {unique_types} alert types detected")
    print("   Consider adding more diverse transaction patterns.")
else:
    print(f"\n✅ GOOD: {unique_types} different alert types detected")

print("\n" + "="*70)

db.close()
