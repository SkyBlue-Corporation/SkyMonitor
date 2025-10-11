from flask import Blueprint, render_template
import os
import json

main = Blueprint('main', __name__)

@main.route('/')
def dashboard():
    #Read of métrics from a file JSON generate script

    data_file = 'scripts/metrics.json'
    if os.path.exists(data_file):
        with open(data_file) as f:
            metrics = json.loads(f)
    else:
        metrics = {}
    return render_template('dashboard.html', metrics=metrics)
