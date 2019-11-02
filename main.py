try:
    import config
except Exception:
    import config_default as config
import celery
import os


app = celery.Celery("HelloJudge2", broker=config.REDIS_URI)
basedir = os.path.dirname(__file__)
# from test.qwq import client as docker_client
import docker
docker_client = docker.from_env()
import task