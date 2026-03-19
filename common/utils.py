from datetime import datetime

from django.utils import timezone


def parse_date(date_str):
    if date_str:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            pass
    return timezone.localdate()


def get_timer_format(seconds):
    hours = int(seconds) // 3600
    minutes = int(seconds) // 60 % 60
    seconds = int(seconds) % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
