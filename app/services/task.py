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
    def delete_memory(memory_id):
        memory = db.session.query(Memory).filter(Memory.id == memory_id).first()
        if not memory:
            raise ValueError(f"未找到 ID 为 {memory_id} 的记忆")
            
        db.session.delete(memory)
        db.session.commit()
        return True

    @staticmethod
    def search_memories(user_id, query, top_k=5):
        # 1. 生成查询文本的嵌入向量
        embedding_service = EmbeddingService()
        query_vector = embedding_service.generate_embedding(query)
        
        # 2. 使用 pgvector 在数据库中搜索
        # 余弦距离: <=>
        # L2 距离: <->
        # 内积: <#>
        # 我们通常使用余弦距离进行嵌入比较，所以按余弦距离排序
        
        stmt = db.session.query(
            Memory, 
            Memory.embedding.cosine_distance(query_vector).label('distance')
        ).filter(
            Memory.user_id == user_id
        ).order_by(
            Memory.embedding.cosine_distance(query_vector)
        ).limit(top_k)
        
        results = stmt.all()
        
        # 3. 更新检索到的记忆的 last_accessed_at
        from sqlalchemy import func
        if results:
            memory_ids = [m.id for m, _ in results]
            db.session.query(Memory).filter(Memory.id.in_(memory_ids)).update(
                {Memory.last_accessed_at: func.now()},
                synchronize_session=False
            )
            db.session.commit()
        
        # 4. 格式化结果
        output = []
        for memory, distance in results:
            output.append({
                'type': memory.type.value,
                'content': memory.content,
                'score': 1 - distance, # 将距离转换为相似度分数
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
    def create_memory_task(user_input, user_id, llm_output):
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
            args=[new_task.id, user_input, user_id, llm_output],
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
