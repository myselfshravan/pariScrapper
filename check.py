from screeninfo import get_monitors

for monitor in get_monitors():
    print(f"Monitor: {monitor}")
