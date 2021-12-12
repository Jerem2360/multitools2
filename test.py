import os

result = b""
while True:
    char = os.read(0, 1)
    result += char
    if char.endswith(b"\n"):
        break

print(result)

