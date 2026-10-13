"""Gunicorn hooks: the email outbox worker runs inside each web worker.

Gunicorn reads ./gunicorn.conf.py by itself, so the start command (Procfile,
Railway) stays as it is. Only hooks live here; every setting still comes
from the command line.

The outbox is the email_outbox table; the thread is only its executor, so
stopping or killing a worker loses no email (backend/app/services/email_outbox.py).
"""


def post_worker_init(worker):
    from backend.app.services.email_outbox import start_worker

    start_worker(worker.wsgi)


def worker_exit(server, worker):
    from backend.app.services.email_outbox import stop_worker

    stop_worker(timeout=10)
