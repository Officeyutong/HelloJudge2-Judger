try:
    import config
except Exception:
    import config_default as config
import celery
import os


app = celery.Celery("HelloJudge2", broker=config.REDIS_URI)
basedir = os.path.dirname(__file__)
import sys
sys.path.append(basedir)
sys.path.append(basedir+"/judgers")
import judgers.remote_runners
JUDGE_CLIENTS = {
    "luogu" : judgers.remote_runners.luogu
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

