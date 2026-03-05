from ..extensions import db
from datetime import datetime

class Task(db.Model):
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(36), unique=True, nullable=False)
    message = db.Column(db.Text)  # Changed from String(255) to Text for longer user input
    status = db.Column(db.String(20), default='pending') # pending, running, completed, failed
    result = db.Column(db.Text, nullable=True)
    error = db.Column(db.Text, nullable=True) # To store failure reason
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'message': self.message,
            'status': self.status,
            'result': self.result,
            'error': self.error,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
