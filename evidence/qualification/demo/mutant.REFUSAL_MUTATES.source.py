def assemble(a, b, f, q):
    if q <= 0:
        return (False, a, b, f + 1)
    if a < 2*q or b < q:
        return (False, a, b, f + 1)
    return (True, a - 2*q, b - q, f + q)
