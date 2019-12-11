import inspect
import ctypes
import urllib.parse
import urllib.request
from contextlib import contextmanager
import requests

def http_post(url: str, data: dict = {})->bytes:
    with requests.post(url, data=data) as urlf:
        # data = urlf.read()
        return urlf.content


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


def _async_raise(tid, exctype):
    """raises the exception, performs cleanup if needed"""
    tid = ctypes.c_long(tid)
    if not inspect.isclass(exctype):
        exctype = type(exctype)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
        tid, ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
        # """if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect"""
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")


def stop_thread(thread):
    _async_raise(thread.ident, SystemExit)

def read_file(x):
    with open(x,"r") as f:
        return f.read()