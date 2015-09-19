from datetime import datetime

def unix_time(dt):
    epoch = datetime.utcfromtimestamp(0)
    delta = dt - epoch
    return int(round(delta.total_seconds()))

def format_time(unix_time):
    if isinstance(unix_time, str):
        unix_time = int(unix_time)
    return datetime.fromtimestamp(unix_time).strftime('%Y-%m-%d %H:%M:%S')
