from celery import shared_task
from ..extensions import db
from ..models.task import Task
from ..models.memory import Memory, MemoryType
from ..services.llm import LLMService
from ..services.embedding import EmbeddingService
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def process_memory_addition(self, task_db_id, user_input, user_id):
    """
    Async task to process memory addition:
    1. Update task status to running
    2. Call LLM to extract info
    3. Call Embedding service
    4. Save to Memory table
    5. Update task status to completed
    """
    try:
        # 1. Update task status to running
        task_record = db.session.get(Task, task_db_id)
        if not task_record:
            logger.error(f"Task record {task_db_id} not found")
            return
            
        task_record.status = 'running'
        db.session.commit()
        
        # 2. Call LLM to extract info
        llm_service = LLMService()
        extraction_result = llm_service.extract_memory_info(user_input)
        
        memory_type_str = extraction_result.get('type', 'fact').upper()
        memory_content = extraction_result.get('content', user_input)
        
        # Validate memory type
        try:
            memory_type = MemoryType[memory_type_str]
        except KeyError:
            memory_type = MemoryType.FACT
            
        # 3. Call Embedding service
        embedding_service = EmbeddingService()
        vector = embedding_service.generate_embedding(memory_content)
        
        # 4. Save to Memory table
        new_memory = Memory(
            user_id=user_id,
            type=memory_type,
            content=memory_content,
            embedding=vector
        )
        db.session.add(new_memory)
        
        # 5. Update task status to completed
        task_record.status = 'completed'
        task_record.result = f"Memory added successfully. ID: {new_memory.id}"
        db.session.commit()
        
        return {"status": "completed", "memory_id": str(new_memory.id)}
        
    except Exception as e:
        logger.error(f"Error processing memory addition: {str(e)}")
        # Handle failure
        db.session.rollback()
        task_record = db.session.get(Task, task_db_id)
        if task_record:
            task_record.status = 'failed'
            task_record.error = str(e)
            db.session.commit()
        raise e
