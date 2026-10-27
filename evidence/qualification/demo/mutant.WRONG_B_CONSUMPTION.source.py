def assemble(a, b, f, q):
    if q <= 0:
        return (False, a, b, f)
    if a < 2*q or b < q:
        return (False, a, b, f)
    return (True, a - 2*q, b - 2*q, f + q)
