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
    异步处理记忆添加任务：
    1. 更新任务状态为运行中
    2. 调用 LLM 提取信息（综合用户输入）
    3. 调用 Embedding 服务
    4. 保存到 Memory 表
    5. 更新任务状态为已完成
    """
    try:
        # 1. 更新任务状态为运行中
        task_record = db.session.get(Task, task_db_id)
        if not task_record:
            logger.error(f"未找到 ID 为 {task_db_id} 的任务记录")
            return
            
        task_record.status = 'running'
        db.session.commit()
        
        # 2. 调用 LLM 提取信息
        # 获取现有记忆用于去重（排除 historical_context）
        existing_memories = db.session.query(Memory).filter(
            Memory.user_id == user_id,
            Memory.type != MemoryType.HISTORICAL_CONTEXT
        ).all()
        # 格式化为字典列表：[{'type': 'position', 'content': '...'}]
        existing_memory_data = [{'type': m.type.value, 'content': m.content} for m in existing_memories]

        llm_service = LLMService()
        
        # 1. 提取标准记忆（position, work_content, writing_preference）
        extraction_results = llm_service.extract_memory_info(user_input, existing_memory_data)
        
        # 2. 提取历史上下文（始终提取一条，且始终锁定）
        historical_context = llm_service.extract_historical_context(user_input)
        
        # 合并结果
        final_results = []
        if extraction_results:
            final_results.extend(extraction_results)
        
        if historical_context:
            historical_context['locked'] = True # 强制锁定历史上下文
            final_results.append(historical_context)
        
        if not final_results:
            task_record.status = 'completed'
            task_record.result = "未在输入中提取到有效记忆。"
            db.session.commit()
            return {"status": "completed", "memory_ids": []}

        memory_ids = []
        embedding_service = EmbeddingService()

        for item in final_results:
            memory_type_str = item.get('type', 'fact').upper()
            memory_content = item.get('content', '')
            is_locked = item.get('locked', False)
            
            if not memory_content:
                continue

            # 验证记忆类型
            try:
                memory_type = MemoryType[memory_type_str]
            except KeyError:
                memory_type = MemoryType.HISTORICAL_CONTEXT
                
            # 3. 调用 Embedding 服务
            vector = embedding_service.generate_embedding(memory_content)
            
            # 4. 保存到 Memory 表
            new_memory = Memory(
                user_id=user_id,
                type=memory_type,
                content=memory_content,
                embedding=vector,
                locked=is_locked
            )
            db.session.add(new_memory)
            # 刷新以获取 ID
            db.session.flush() 
            memory_ids.append(str(new_memory.id))
        
        # 5. 更新任务状态为已完成
        task_record.status = 'completed'
        task_record.result = f"记忆添加成功。ID列表: {', '.join(memory_ids)}"
        db.session.commit()
        
        return {"status": "completed", "memory_ids": memory_ids}
        
    except Exception as e:
        logger.error(f"处理记忆添加任务失败: {str(e)}")
        # Handle failure
        db.session.rollback()
        task_record = db.session.get(Task, task_db_id)
        if task_record:
            task_record.status = 'failed'
            task_record.error = str(e)
            db.session.commit()
        raise e
