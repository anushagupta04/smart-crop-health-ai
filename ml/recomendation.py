"""
Recommendation engine - imported by app.py
All recommendations are now embedded directly in app.py's RECOMMENDATIONS dict.
This file is kept for standalone usage / CLI access.
"""

URGENCY_LEVELS = {
    "none":     "✅ No Action Needed",
    "medium":   "⚠️  Action Recommended",
    "high":     "🔴 Urgent Action Required",
    "critical": "🚨 CRITICAL - Act Immediately"
}

def get_urgency_label(urgency: str) -> str:
    return URGENCY_LEVELS.get(urgency, "-")


def format_recommendation(rec: dict, disease_label: str) -> str:
    sep = "─" * 50
    lines = [
        f"\n{'═'*50}",
        f"  🌿 CropSense AI - Disease Report",
        f"{'═'*50}",
        f"  Disease : {disease_label}",
        f"  Urgency : {get_urgency_label(rec.get('urgency','medium'))}",
        sep,
        f"\n📋 Description:\n  {rec.get('description','')}",
        f"\n⚡ Immediate Actions:"
    ]
    for a in rec.get("immediate_actions", []):
        lines.append(f"  → {a}")
    lines.append(f"\n💊 Treatments:")
    for t in rec.get("treatments", []):
        lines.append(f"  → {t}")
    lines.append(f"\n🛡️ Prevention:")
    for p in rec.get("prevention", []):
        lines.append(f"  → {p}")
    lines.append(f"\n🌱 Fertilizer Advice:\n  {rec.get('fertilizer','')}")
    lines.append(f"\n{'═'*50}\n")
    return "\n".join(lines)
