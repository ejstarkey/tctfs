from flask import Blueprint, render_template
from ...models.storm import Storm

web_bp = Blueprint("web", __name__)

@web_bp.route("/")
def dashboard():
    # Placeholder  will show cyclone list later
    storms = Storm.query.all()
    return render_template("dashboard.html.j2", storms=storms)

