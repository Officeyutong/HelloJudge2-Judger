try:
    import config
except Exception:
    import config_default as config
import celery
import os
import common

app = celery.Celery("HelloJudge2", broker=config.REDIS_URI)
basedir = os.path.dirname(__file__)
import sys
sys.path.append(basedir)
sys.path.append(basedir+"/judgers")
import judgers.remote_runners.luogu
# import judgers.remote_runners.vjudge
import judgers.remote_runners.uoj
import judgers.remote_runners.poj
JUDGE_CLIENTS = {
    "luogu" : judgers.remote_runners.luogu.get_judge_client()(),
    # "vjudge":judgers.remote_runners.vjudge,
    "poj" : judgers.remote_runners.poj.get_judge_client()(),
    "uoj" : judgers.remote_runners.uoj.get_judge_client()("http://uoj.ac","uoj","UOJSESSID"),
    "darkbzoj" : judgers.remote_runners.uoj.get_judge_client()("http://darkbzoj.tk/","darkbzoj","PHPSESSID")
}

# from test.qwq import client as docker_client
import docker
docker_client = docker.from_env()
if config.ENABLE_IDE_RUN:
    import judgers.ide_run
if config.ENABLE_LOCAL_JUDGE:
    import judgers.local
if config.ENABLE_REMOTE_JUDGE:
    import judgers.remote

