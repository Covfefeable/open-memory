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
        # 1. 构建查询
        query = db.session.query(Memory).filter(Memory.user_id == user_id)
        
        if memory_type_str:
            try:
                memory_type = MemoryType[memory_type_str.upper()]
                query = query.filter(Memory.type == memory_type)
            except KeyError:
                # 如果类型无效，返回空列表
                return []
        
        # 2. 执行查询
        memories = query.order_by(Memory.created_at.desc()).all()
        
        # 3. 格式化输出
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
            raise ValueError(f"无效的记忆类型: {memory_type_str}")
            
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
    def delete_memories(memory_ids):
        if not memory_ids:
            return True
            
        # 查找所有要删除的记忆
        memories = db.session.query(Memory).filter(Memory.id.in_(memory_ids)).all()
        
        if not memories:
            # 如果没有找到任何记录，可以根据需求抛出异常或仅返回
            # 这里选择如果传入了ID但没找到，不视为严重错误，或者可以抛出未找到的部分ID
            pass
            
        if len(memories) != len(set(memory_ids)):
            # 可选：检查是否所有ID都存在
            pass

        # 批量删除
        db.session.query(Memory).filter(Memory.id.in_(memory_ids)).delete(synchronize_session=False)
        db.session.commit()
        return True

    @staticmethod
    def search_memories(user_id, query, basic_topk=5, history_topk=5, basic_score=None, history_score=None):
        # 1. 生成查询文本的嵌入向量
        embedding_service = EmbeddingService()
        query_vector = embedding_service.generate_embedding(query)
        
        # 2. 分别检索基础记忆和历史对话核心内容
        
        # 基础记忆类型
        basic_types = [
            MemoryType.POSITION,
            MemoryType.WORK_CONTENT,
            MemoryType.WRITING_PREFERENCE
        ]
        
        # 检索基础记忆
        basic_query = db.session.query(
            Memory, 
            Memory.embedding.cosine_distance(query_vector).label('distance')
        ).filter(
            Memory.user_id == user_id,
            Memory.type.in_(basic_types)
        ).order_by(
            Memory.embedding.cosine_distance(query_vector)
        ).limit(basic_topk)
        
        # 检索历史对话核心内容
        history_query = db.session.query(
            Memory, 
            Memory.embedding.cosine_distance(query_vector).label('distance')
        ).filter(
            Memory.user_id == user_id,
            Memory.type == MemoryType.HISTORICAL_CONTEXT
        ).order_by(
            Memory.embedding.cosine_distance(query_vector)
        ).limit(history_topk)
        
        basic_results = basic_query.all()
        history_results = history_query.all()
        
        # 3. 合并结果并进行分数过滤
        combined_results = []
        
        # 处理基础记忆
        for memory, distance in basic_results:
            score = 1 - distance
            if basic_score is not None and score < basic_score:
                continue
            combined_results.append((memory, score))
            
        # 处理历史记忆
        for memory, distance in history_results:
            score = 1 - distance
            if history_score is not None and score < history_score:
                continue
            combined_results.append((memory, score))
        
        # 4. 更新检索到的记忆的 last_accessed_at
        from sqlalchemy import func
        if combined_results:
            memory_ids = [m.id for m, _ in combined_results]
            db.session.query(Memory).filter(Memory.id.in_(memory_ids)).update(
                {Memory.last_accessed_at: func.now()},
                synchronize_session=False
            )
            db.session.commit()
        
        # 5. 格式化结果
        output = []
        # 按分数从高到低排序最终结果
        combined_results.sort(key=lambda x: x[1], reverse=True)
        
        for memory, score in combined_results:
            output.append({
                'type': memory.type.value,
                'content': memory.content,
                'score': score,
                'created_at': memory.created_at.isoformat() if memory.created_at else None
            })
            
        return output

    @staticmethod
    def create_background_task(message):
        # 1. 启动 Celery 任务
        # 在此处重新导入以避免循环依赖，或者确保 process_message 存在
        from ..tasks.background import process_message
        celery_task = process_message.delay(message)
        
        # 2. 记录到数据库
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
        # 1. 预先生成任务 ID 以便先保存到数据库
        # 注意：我们需要数据库 ID 传递给任务，或者传递 celery 任务 ID。
        # 这里先创建一个带有临时任务 ID 或生成 UUID 的数据库记录
        
        task_uuid = str(uuid.uuid4())
        
        new_task = Task(
            task_id=task_uuid,
            message=user_input, # 将输入存储在 message 字段中
            status='running'
        )
        db.session.add(new_task)
        db.session.commit()
        
        # 2. 启动 Celery 任务
        # 传递数据库主键 ID，以便任务可以更新记录
        celery_task = process_memory_addition.apply_async(
            args=[new_task.id, user_input, user_id],
            task_id=task_uuid # 使用相同的 ID 作为 celery ID
        )
        
        return task_uuid
        
    @staticmethod
    def get_task_status(task_id):
        # 1. 先检查数据库
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
