from functools import wraps
from flask import jsonify, redirect
from flask_login import current_user, login_required as flask_login_required

def premium_required(f):
    @wraps(f)
    @flask_login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_premium:
            return redirect("/premium")
        return f(*args, **kwargs)
    return wrapper



def api_premium_required(f):
    """JSON twin of ``premium_required`` for API routes: 401 signed out, 403 without Premium."""

    @wraps(f)
    @flask_login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_premium:
            return jsonify({"error": "premium_required"}), 403
        return f(*args, **kwargs)

    return wrapper
