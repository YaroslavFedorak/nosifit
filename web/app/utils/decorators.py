from functools import wraps
from flask import redirect
from flask_login import current_user, login_required as flask_login_required

def premium_required(f):
    @wraps(f)
    @flask_login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_premium:
            return redirect("/premium")
        return f(*args, **kwargs)
    return wrapper
