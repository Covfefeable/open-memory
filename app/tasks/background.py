from celery import shared_task
from sqlalchemy import select, func, text
from ..extensions import db
from ..models.memory import Memory, MemoryType
from ..services.llm import LLMService
from ..services.embedding import EmbeddingService
import logging

logger = logging.getLogger(__name__)

@shared_task
def compress_user_memories():
    """
    Periodic task to compress memories for users with > 50 records.
    Runs every 5 minutes (configured in celery beat schedule).
    """
    try:
        logger.info("Starting scheduled compression check...")
        
        # 1. Find users with > 50 memories
        # Group by user_id and count
        users_with_many_memories = db.session.query(
            Memory.user_id
        ).group_by(
            Memory.user_id
        ).having(
            func.count(Memory.id) > 50
        ).all()
        
        if not users_with_many_memories:
            logger.info("No users found eligible for compression.")
            return "No users eligible"
            
        logger.info(f"Found {len(users_with_many_memories)} users eligible for compression.")
        
        for (user_id,) in users_with_many_memories:
            logger.info(f"Triggering compression task for user {user_id}")
            process_user_memory_compression.delay(user_id)
            
        return f"Triggered compression for {len(users_with_many_memories)} users"
        
    except Exception as e:
        logger.error(f"Error in compress_user_memories: {str(e)}")
        return f"Error: {str(e)}"

@shared_task
def process_user_memory_compression(user_id):
    """
    Compress memories for a specific user.
    1. Fetch all memories
    2. Send to LLM for summarization/deduplication
    3. Save new memories
    4. Delete old memories
    """
    try:
        logger.info(f"[Compression] Starting for user {user_id}")
        
        # 1. Fetch all memories
        memories = db.session.query(Memory).filter(
            Memory.user_id == user_id
        ).order_by(Memory.created_at).all()
        
        logger.info(f"[Compression] Fetched {len(memories)} memories for user {user_id}")
        
        if len(memories) <= 50:
            logger.info(f"[Compression] Skipped for user {user_id}: Memory count {len(memories)} <= 50")
            return "Skipped: Memory count dropped below threshold"
            
        # Prepare content for LLM
        memory_texts = [f"- {m.content} (Type: {m.type.value})" for m in memories]
        combined_text = "\n".join(memory_texts)
        
        logger.info(f"[Compression] Calling LLM to compress {len(memories)} items...")
        
        # 2. Call LLM
        llm_service = LLMService()
        # We need a specific method for summarization
        new_memories_data = llm_service.compress_memories(combined_text)
        
        logger.info(f"[Compression] LLM returned {len(new_memories_data)} items")
        
        if not new_memories_data:
            logger.warning(f"[Compression] LLM returned no compressed memories for user {user_id}")
            return "Failed: LLM returned empty result"
            
        # Check if compression actually reduced count
        if len(new_memories_data) >= len(memories):
            logger.info(f"[Compression] Compression didn't reduce count for user {user_id} ({len(memories)} -> {len(new_memories_data)}). Keeping originals.")
            return "Skipped: No reduction in memory count"
            
        # 3. Save new memories
        logger.info(f"[Compression] Generating embeddings for new memories...")
        embedding_service = EmbeddingService()
        new_memory_objects = []
        
        for item in new_memories_data:
            memory_content = item.get('content')
            memory_type_str = item.get('type', 'fact').upper()
            
            try:
                memory_type = MemoryType[memory_type_str]
            except KeyError:
                memory_type = MemoryType.FACT
                
            vector = embedding_service.generate_embedding(memory_content)
            
            new_memory = Memory(
                user_id=user_id,
                type=memory_type,
                content=memory_content,
                embedding=vector
            )
            new_memory_objects.append(new_memory)
            
        # Transaction: Add new, delete old
        try:
            logger.info(f"[Compression] Saving to database: Adding {len(new_memory_objects)} new, Deleting {len(memories)} old")
            
            # Add new
            db.session.add_all(new_memory_objects)
            
            # Delete old
            # We delete by ID to ensure we only delete the ones we fetched
            old_ids = [m.id for m in memories]
            db.session.query(Memory).filter(Memory.id.in_(old_ids)).delete(synchronize_session=False)
            
            db.session.commit()
            logger.info(f"[Compression] SUCCESS for user {user_id}. Compressed {len(memories)} -> {len(new_memory_objects)}")
            return f"Compressed {len(memories)} -> {len(new_memory_objects)}"
            
        except Exception as db_err:
            db.session.rollback()
            logger.error(f"[Compression] Database error during save for user {user_id}: {str(db_err)}")
            raise db_err
            
    except Exception as e:
        logger.error(f"[Compression] Critical error for user {user_id}: {str(e)}")
        return f"Error: {str(e)}"