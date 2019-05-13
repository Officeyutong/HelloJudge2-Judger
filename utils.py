import urllib.parse
import urllib.request
from contextlib import contextmanager


def http_post(url: str, data: dict = {})->bytes:
    with urllib.request.urlopen(url, data=urllib.parse.urlencode(data).encode()) as urlf:
        data = urlf.read()
        return data


def decode_json(obj):
    import json
    return json.JSONDecoder().decode(obj)


def encode_json(obj):
    import json
    return json.JSONEncoder().encode(obj)


def time_limit_exec(seconds, message, target):
    import threading
    import time
    thread = threading.Thread(target=target)
    thread.start()
    begin = time.time()
    while thread.isAlive() and time.time()-begin < seconds:
        time.sleep(0.001)
    if thread.isAlive():
        raise TimeoutError(
            f"Timeout for {message}", time.time()-begin)
    else:
        return time.time()-begin
