hexcode = lambda s: s.replace(" ", "").decode('hex')

# Encoder produces this code, decoder reads it.
header = hexcode("89 4C 49 43 0D 0A 1A 0A")

