import datetime


def now() -> str:
    return datetime.datetime.now(tz=datetime.UTC).isoformat()
