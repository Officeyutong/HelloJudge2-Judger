try:
    import config
except Exception:
    import config_default as config
import celery

app = celery.Celery("HelloJudge2", broker=config.REDIS_URI)
import task
import os
basedir=os.path.dirname(__file__)