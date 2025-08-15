import time, random

def with_backoff(fn, max_retries=4, base=0.8, cap=8.0):
    for i in range(max_retries):
        try:
            return fn()
        except Exception:
            if i == max_retries - 1:
                raise
            sleep = min(cap, base * (2 ** i)) * (1 + 0.1 * random.random())
            time.sleep(sleep)
