from datetime import datetime


def parse(text):
    """Dates come from the regional office export."""
    for fmt in ("%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognized date {text!r}")


def days_between(start, end):
    return (parse(end) - parse(start)).days
