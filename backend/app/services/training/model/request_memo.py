"""Results of the training model, shared within one HTTP request.

One dashboard or recovery request asks for the same analysis several times:
the training recommendations, the recovery notes and the readiness score
each analyse the same user for the same day, and each analysis costs seven
queries. The first result is kept on the request and reused by the others.

- The memo lives in the WSGI environ of the current request, so it can never
  carry over to another request (tests reuse one app context, and with it
  ``flask.g``, across many requests; the environ is new every time).
- Only reads (GET, HEAD) use it: a request that writes always recomputes.
  And any write clears it (a flush, a commit or a rollback, so statements
  run without the ORM count too): a read that saves something on the way
  (a daily snapshot) recomputes after that write.
- Outside a request (scripts, the shell) nothing is cached.
- The cached objects are shared, so callers must only read them, which is
  what every caller of the model does.
"""

from flask import has_request_context, request
from sqlalchemy import event
from sqlalchemy.orm import Session

_ENVIRON_KEY = "nosifit.training_model_memo"


SAFE_METHODS = frozenset({"GET", "HEAD"})


def _memo():
    if not has_request_context() or request.method not in SAFE_METHODS:
        return None
    return request.environ.setdefault(_ENVIRON_KEY, {})


def remembered(key, compute):
    """``compute()`` once per request for each ``key``."""
    memo = _memo()
    if memo is None:
        return compute()
    if key not in memo:
        memo[key] = compute()
    return memo[key]


def forget() -> None:
    if has_request_context():
        request.environ.pop(_ENVIRON_KEY, None)


@event.listens_for(Session, "after_flush")
def _forget_after_flush(session, flush_context):
    forget()


@event.listens_for(Session, "after_commit")
@event.listens_for(Session, "after_rollback")
def _forget_after_transaction(session):
    forget()
