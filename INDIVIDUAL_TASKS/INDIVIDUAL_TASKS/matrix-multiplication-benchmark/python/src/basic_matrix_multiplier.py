

def multiply(a, b):
    n = len(a)
    c = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            total = 0.0
            for k in range(n):
                total += a[i][k] * b[k][j]
            c[i][j] = total
    return c


def checksum(m):
    s = 0.0
    for row in m:
        for x in row:
            s += x
    return s
