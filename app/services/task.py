from ..models.task import Task
from ..tasks.background import process_message
from ..tasks.memory import process_memory_addition
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
    def create_memory_task(user_input, user_id):
        # 1. Generate task ID beforehand to save to DB first
        # Note: We need the DB ID to pass to the task, or we pass the celery task ID.
        # Let's create the DB record first with a temporary task_id or generate UUID
        
        task_uuid = str(uuid.uuid4())
        
        new_task = Task(
            task_id=task_uuid,
            message=user_input, # Storing input in message field
            status='running'
        )
        db.session.add(new_task)
        db.session.commit()
        
        # 2. Start Celery task
        # Pass the DB primary key ID so the task can update the record
        celery_task = process_memory_addition.apply_async(
            args=[new_task.id, user_input, user_id],
            task_id=task_uuid # Use same ID for celery
        )
        
        return task_uuid
        
    @staticmethod
    def get_task_status(task_id):
        # 1. Check DB first
        task_record = Task.query.filter_by(task_id=task_id).first()
        
        if not task_record:
            return {'status': 'not_found'}
            
        return {
            'task_id': task_id,
            'status': task_record.status,
            'result': task_record.result,
            'error': task_record.error,
            'created_at': task_record.created_at.isoformat(),
            'updated_at': task_record.updated_at.isoformat() if task_record.updated_at else None
        }
