def allocate(available, reserved, q):
    if q <= 0 or available < q:
        return (False, available, reserved)
    return (True, available - q, reserved + q)
