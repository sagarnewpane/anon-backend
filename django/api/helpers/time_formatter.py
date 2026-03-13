from datetime import timedelta

def format_timeago(delta):
    if delta > timedelta(days=1):
        return f"{delta.days}d ago"
    elif delta > timedelta(hours=1):
        return f"{delta.seconds // 3600}h ago"
    elif delta > timedelta(minutes=1):
        return f"{delta.seconds // 60}m ago"
    else:
        return "Just now"
