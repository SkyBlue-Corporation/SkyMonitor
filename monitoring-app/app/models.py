from app import db
from datetime import datetime

class Server(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(15), nullable=False)
    status = db.Column(db.String(20), default='unknown')
    cpu_usage = db.Column(db.Float, default=0.0)
    memory_usage = db.Column(db.Float, default=0.0)
    storage_usage = db.Column(db.Float, default=0.0)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    type = db.Column(db.String(20), default='server')
