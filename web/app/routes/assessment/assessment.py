from flask import Blueprint, render_template

assessment_bp = Blueprint(
    "assessment",
    __name__,
    url_prefix="/assessment"
)

@assessment_bp.get("/")
def assessment_home():
    return "Assessment module is working"
