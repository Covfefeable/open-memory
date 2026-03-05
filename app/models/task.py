from ..extensions import db
from datetime import datetime

class Task(db.Model):
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(36), unique=True, nullable=False)
    message = db.Column(db.String(255))
    status = db.Column(db.String(20), default='pending')
    result = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'message': self.message,
            'status': self.status,
            'result': self.result,
            'created_at': self.created_at.isoformat()
        }
