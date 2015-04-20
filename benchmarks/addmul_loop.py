j = 0
while j < 500:
    k = 0
    while k < 5000000:
        assert k+j*k >= 0
        k += 1
    j += 1
