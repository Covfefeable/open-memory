from ..models.task import Task
from ..tasks.memory import process_memory_addition
from ..extensions import db
import uuid

from ..models.memory import Memory, MemoryType
from ..services.embedding import EmbeddingService
from sqlalchemy import select, and_

class TaskService:
    @staticmethod
    def list_memories(user_id, memory_type_str=None):
        # 1. Build query
        query = db.session.query(Memory).filter(Memory.user_id == user_id)
        
        if memory_type_str:
            try:
                memory_type = MemoryType[memory_type_str.upper()]
                query = query.filter(Memory.type == memory_type)
            except KeyError:
                # If invalid type, just return empty or ignore filter? 
                # Let's return empty to be safe
                return []
        
        # 2. Execute
        memories = query.order_by(Memory.created_at.desc()).all()
        
        # 3. Format
        output = []
        for m in memories:
            output.append({
                'id': str(m.id),
                'type': m.type.value,
                'content': m.content,
                'locked': m.locked,
                'created_at': m.created_at.isoformat(),
                'last_accessed_at': m.last_accessed_at.isoformat() if m.last_accessed_at else None
            })
        return output

    @staticmethod
    def manual_add_memory(user_id, content, memory_type_str='fact'):
        try:
            memory_type = MemoryType[memory_type_str.upper()]
        except KeyError:
            raise ValueError(f"Invalid memory type: {memory_type_str}")
            
        embedding_service = EmbeddingService()
        vector = embedding_service.generate_embedding(content)
        
        memory = Memory(
            user_id=user_id,
            type=memory_type,
            content=content,
            embedding=vector
        )
        
        db.session.add(memory)
        db.session.commit()
        
        return {
            'id': str(memory.id),
            'user_id': memory.user_id,
            'type': memory.type.value,
            'content': memory.content,
            'locked': memory.locked,
            'created_at': memory.created_at.isoformat() if memory.created_at else None
        }

    @staticmethod
    def update_memory(memory_id, content=None, memory_type_str=None, locked=None):
        memory = db.session.query(Memory).filter(Memory.id == memory_id).first()
        if not memory:
            raise ValueError(f"Memory with id {memory_id} not found")
            
        if content:
            memory.content = content
            # Re-generate embedding if content changed
            embedding_service = EmbeddingService()
            memory.embedding = embedding_service.generate_embedding(content)
            
        if memory_type_str:
            try:
                memory.type = MemoryType[memory_type_str.upper()]
            except KeyError:
                pass # Ignore invalid type or raise error?
        
        if locked is not None:
            memory.locked = bool(locked)
                
        db.session.commit()
        
        return {
            'id': str(memory.id),
            'type': memory.type.value,
            'content': memory.content,
            'locked': memory.locked,
            'updated_at': memory.updated_at.isoformat() if memory.updated_at else None
        }

    @staticmethod
    def delete_memory(memory_id):
        memory = db.session.query(Memory).filter(Memory.id == memory_id).first()
        if not memory:
            raise ValueError(f"Memory with id {memory_id} not found")
            
        db.session.delete(memory)
        db.session.commit()
        return True

    @staticmethod
    def search_memories(user_id, query, top_k=5):
        # 1. Generate embedding for query
        embedding_service = EmbeddingService()
        query_vector = embedding_service.generate_embedding(query)
        
        # 2. Search in DB using pgvector
        # Cosine distance: <=>
        # L2 distance: <->
        # Inner product: <#>
        # We usually use cosine distance for embeddings, so we order by cosine distance
        
        stmt = db.session.query(
            Memory, 
            Memory.embedding.cosine_distance(query_vector).label('distance')
        ).filter(
            Memory.user_id == user_id
        ).order_by(
            Memory.embedding.cosine_distance(query_vector)
        ).limit(top_k)
        
        results = stmt.all()
        
        # 3. Update last_accessed_at for retrieved memories
        from sqlalchemy import func
        if results:
            memory_ids = [m.id for m, _ in results]
            db.session.query(Memory).filter(Memory.id.in_(memory_ids)).update(
                {Memory.last_accessed_at: func.now()},
                synchronize_session=False
            )
            db.session.commit()
        
        # 4. Format results
        output = []
        for memory, distance in results:
            output.append({
                'type': memory.type.value,
                'content': memory.content,
                'score': 1 - distance, # Convert distance to similarity score
                'created_at': memory.created_at.isoformat() if memory.created_at else None
            })
            
        return output

    @staticmethod
    def create_background_task(message):
        # 1. Start Celery task
        # Re-import here to avoid circular dependency if needed, or ensure process_message exists
        from ..tasks.background import process_message
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
    def create_memory_task(user_input, user_id, llm_output):
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
            args=[new_task.id, user_input, user_id, llm_output],
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
