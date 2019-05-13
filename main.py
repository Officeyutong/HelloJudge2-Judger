try:
    import config
except Exception:
    import config_default as config
import celery
import os
import task

app = celery.Celery("HelloJudge2", broker=config.REDIS_URI)
basedir = os.path.dirname(__file__)
