"""Daily scores. Pure functions, no DB."""

from statistics import mean, pstdev

from app.ml.distraction import TH

# Weights for the overall focus score
W_RATIO = 0.4
W_SESSION = 0.3
W_SWITCH = 0.2
W_NOTIF = 0.1

# Session of this length (or more) gets full marks
TARGET_SESSION_MIN = 25

PRODUCTIVE = (
    "code",
    "pycharm",
    "visual studio",
    "terminal",
    "powershell",
    "cmd",
    "github",
    "notion",
    "word",
    "excel",
    "powerpoint",
    "docs",
    "figma",
    "leetcode",
    "stackoverflow",
    "obsidian",
)

UNPRODUCTIVE = (
    "youtube",
    "instagram",
    "facebook",
    "twitter",
    "netflix",
    "reddit",
    "whatsapp",
    "discord",
    "snapchat",
    "telegram",
    "primevideo",
)

SYSTEM_APPS = (
    "explorer",
    "searchhost",
    "searchapp",
    "shellexperiencehost",
    "startmenuexperiencehost",
    "applicationframehost",
    "lockapp",
    "taskmgr",
    "textinputhost",
    "dwm",
)


def _clamp(x, lo=0.0, hi=100.0):
    """Clamp a value between lo and hi."""
    return max(lo, min(hi, x))


def focus_score(f, notif_impact_rate=0.0):
    """
    Calculate the daily focus score (0–100).

    Args:
        f: Features dictionary from build_daily_features().
        notif_impact_rate: Notification impact ratio (0–1).

    Returns:
        float | None
    """
    if f["active_min"] <= 0:
        return None

    ratio = _clamp(f["focus_min"] / f["active_min"] * 100)
    session = _clamp(f["avg_session_min"] / TARGET_SESSION_MIN * 100)

    per_hour = f["switch_count"] / (f["active_min"] / 60)
    switch_pen = _clamp(per_hour / TH.high_switches_per_hour * 100)
    notif_pen = _clamp(notif_impact_rate * 100)

    score = (
        W_RATIO * ratio
        + W_SESSION * session
        + W_SWITCH * (100 - switch_pen)
        + W_NOTIF * (100 - notif_pen)
    )

    return round(score, 2)


def _kind(app):
    """Return app type: productive ('p'), unproductive ('u'), or None."""
    a = app.lower()

    if any(k in a for k in PRODUCTIVE):
        return "p"

    if any(k in a for k in UNPRODUCTIVE):
        return "u"

    return None


def is_productive(app):
    """True if the app is considered productive."""
    return _kind(app) == "p"


def is_system_app(app):
    """True if the app is a Windows system application."""
    a = app.lower()
    return any(k in a for k in SYSTEM_APPS)


def productivity_score(top_apps):
    """
    Calculate productive vs unproductive app ratio.

    Args:
        top_apps: Dict[str, minutes]

    Returns:
        float | None
    """
    productive = 0.0
    unproductive = 0.0

    for app, minutes in top_apps.items():
        kind = _kind(app)

        if kind == "p":
            productive += minutes
        elif kind == "u":
            unproductive += minutes

    if productive + unproductive == 0:
        return None

    return round(productive / (productive + unproductive) * 100, 2)


def completed_lengths_min(focus_sessions):
    """
    Return completed focus session lengths in minutes.
    """
    return [
        (session["ended_at"] - session["started_at"]).total_seconds() / 60
        for session in focus_sessions
        if session["ended_at"] and session["status"] == "completed"
    ]


def stability_score(lengths):
    """
    Measure consistency of focus sessions.

    100 = every session has the same length.

    Uses coefficient of variation.
    Returns None if fewer than two sessions exist.
    """
    if len(lengths) < 2:
        return None

    avg = mean(lengths)

    if avg <= 0:
        return None

    coefficient = pstdev(lengths) / avg
    return round(100 * (1 - min(coefficient, 1.0)), 2)


def trend_slope(values):
    """
    Least-squares slope per day over the given scores.

    Returns None if fewer than three values exist.
    """
    count = len(values)

    if count < 3:
        return None

    x_mean = (count - 1) / 2
    y_mean = mean(values)

    numerator = sum((i - x_mean) * (value - y_mean) for i, value in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(count))

    return round(numerator / denominator, 2)


def trailing_run(day_scores):
    """
    Keep only the final run of consecutive days.

    Args:
        day_scores: List[(date, score)] sorted oldest -> newest.

    Returns:
        List[score]
    """
    run = []
    previous_day = None

    for day, score in day_scores:
        if previous_day is not None and (day - previous_day).days != 1:
            run = []

        run.append(score)
        previous_day = day

    return run