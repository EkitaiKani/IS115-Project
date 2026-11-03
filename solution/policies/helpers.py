

# converts time HH:MM into minutes
def to_minutes(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)

