def insert_or_append(d, key, value):
    if key in d:
        d[key].append(value)
    else:
        d[key] = [value]


def whoami(obj):
    return obj.__class__.__name__