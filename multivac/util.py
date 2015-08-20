from datetime import datetime

def unix_time(dt):
    epoch = datetime.utcfromtimestamp(0)
    delta = dt - epoch
    return int(round(delta.total_seconds()))
