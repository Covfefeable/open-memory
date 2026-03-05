from ..models.task import Task
from ..tasks.background_tasks import process_message
from ..extensions import db
import uuid

class TaskService:
    @staticmethod
    def create_background_task(message):
        # 1. Start Celery task
        celery_task = process_message.delay(message)
        
        # 2. Record in DB
        new_task = Task(
            task_id=celery_task.id,
            message=message,
            status='pending'
        )
        db.session.add(new_task)
        db.session.commit()
        
        return celery_task.id
        
    @staticmethod
    def get_task_status(task_id):
        # 1. Check DB first
        task_record = Task.query.filter_by(task_id=task_id).first()
        
        if not task_record:
            return {'status': 'not_found'}
            
        # 2. Check Celery result backend if pending/processing
        # (For simplicity, we just return DB status, but in real app we might sync here)
        from celery.result import AsyncResult
        res = AsyncResult(task_id)
        
        return {
            'task_id': task_id,
            'status': res.status,
            'result': str(res.result) if res.ready() else None
        }
