"""Template-based insights. Pure functions, no DB."""
from collections import Counter

from app.ml.features import best_hour
from app.ml.focus_score import is_productive
from app.ml.focus_score import is_productive, is_system_app
PRIORITY = ["warning", "fatigue", "leak", "interruptions", "switching", "notification", "pattern", "positive"]


def hour_label(h):
    return f"{h:02d}:00-{(h + 1) % 24:02d}:00"


def attention_leaks(events, top=3):
    """Non-productive apps that pulled the user away most often during focus sessions."""
    c = Counter(
        e["to_app"] for e in events
            if not e["idle"] and e["to_app"] and not is_productive(e["to_app"]) and not is_system_app(e["to_app"])
    )
    return [{"app": a, "interruptions": n} for a, n in c.most_common(top)]


def build_insights(features, scores, leaks, clusters, high_hours, notif, predictions):
    out = []

    def add(t, text):
        out.append({"type": t, "text": text})

    bh = best_hour(features["hourly_focus_min"])
    if bh is None:
        bh = best_hour(features["hourly_active_min"])
    if bh is not None:
        add("pattern", f"Your best focus time is {hour_label(bh)}. Plan your deep work for then.")

    if leaks:
        add("leak", f"{leaks[0]['app']} pulled you away {leaks[0]['interruptions']} time(s) during focus sessions. "
                    "Keep it closed while you focus.")
    if high_hours:
        hrs = ", ".join(hour_label(h) for h in high_hours)
        add("switching", f"You switched apps a lot between {hrs}. Try to do one thing at a time.")
    if clusters:
        add("interruptions", f"You were interrupted 3 or more times within 30 minutes, {len(clusters)} time(s) today. "
                             "Turn on Do Not Disturb at such times.")
    if notif["total"] and notif["impact_rate"] >= 0.5:
        add("notification", f"{int(notif['impact_rate'] * 100)}% of notifications were followed by an app switch. "
                            "Mute notifications while you work.")

    deg = predictions["focus_degradation"]
    if deg["status"] in ("warning", "high"):
        add("warning", f"Your focus score is dropping by about {abs(deg['slope'])} points a day. "
                       "Check your sleep and take regular breaks.")
    if predictions["productivity_risk"]["at_risk"]:
        add("warning", "Your productivity is at risk: " + "; ".join(predictions["productivity_risk"]["reasons"]) + ".")
    if predictions["attention_fatigue"]["fatigued_sessions"] > 0:
        add("fatigue", "Your focus drops after about 90 minutes. Take a 10-minute break every 60 to 75 minutes.")

    fs = scores.get("focus_score")
    if fs is not None and fs >= 70:
        add("positive", f"Great day! Your focus score was {fs}. Keep it up.")
    return out


def daily_summary(day, scores, features, leaks, insights):
    bh = best_hour(features["hourly_focus_min"])
    if bh is None:
        bh = best_hour(features["hourly_active_min"])
    ranked = sorted(insights, key=lambda i: PRIORITY.index(i["type"]) if i["type"] in PRIORITY else 99)
    suggestion = ranked[0]["text"] if ranked else "Start a focus session today. Insights will appear once there is data."
    return {
        "day": day.isoformat(),
        "focus_score": scores.get("focus_score"),
        "productivity_score": scores.get("productivity_score"),
        "stability_score": scores.get("stability_score"),
        "focus_min": features["focus_min"],
        "active_min": features["active_min"],
        "best_hour": hour_label(bh) if bh is not None else None,
        "top_distraction": leaks[0]["app"] if leaks else None,
        "suggestion": suggestion,
    }