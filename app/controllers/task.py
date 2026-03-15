from flask import jsonify
from ..utils.response import success_response, error_response

def create_task(message):
    from ..services.task import TaskService
    
    task_id = TaskService.create_background_task(message)
    return success_response(data={'task_id': task_id})

def get_task(task_id):
    from ..services.task import TaskService
    
    result = TaskService.get_task_status(task_id)
    if result.get('status') == 'not_found':
        return error_response(message="任务不存在", code=404)
    return success_response(data=result)

def add_memory(request):
    from ..services.task import TaskService
    
    data = request.get_json()
    if not data or 'user_input' not in data or 'user_id' not in data:
        return error_response(message='缺少必要参数：user_input 或 user_id', code=400)
    
    task_id = TaskService.create_memory_task(data['user_input'], data['user_id'])
    return success_response(data={'task_id': task_id, 'status': 'running'}, code=202)

def search_memory(request):
    from ..services.task import TaskService
    
    data = request.get_json()
    if not data or 'user_id' not in data or 'query' not in data:
        return error_response(message='缺少必要参数：user_id 或 query', code=400)
        
    user_id = data['user_id']
    query = data['query']
    
    basic_topk = data.get('basic_topk', 5)
    history_topk = data.get('history_topk', 5)
    basic_score = data.get('basic_score')
    history_score = data.get('history_score')
    
    results = TaskService.search_memories(
        user_id, 
        query, 
        basic_topk=basic_topk, 
        history_topk=history_topk,
        basic_score=basic_score,
        history_score=history_score
    )
    return success_response(data=results)

def list_memory(request):
    from ..services.task import TaskService
    
    data = request.get_json()
    if not data or 'user_id' not in data:
        return error_response(message='缺少必要参数：user_id', code=400)
        
    user_id = data['user_id']
    memory_type = data.get('type') # Optional
    
    results = TaskService.list_memories(user_id, memory_type)
    return success_response(data=results)

def manual_add_memory(request):
    from ..services.task import TaskService
    
    data = request.get_json()
    if not data or 'user_id' not in data or 'content' not in data:
        return error_response(message='缺少必要参数：user_id 或 content', code=400)
    
    user_id = data['user_id']
    content = data['content']
    memory_type = data.get('type', 'fact') # Default to fact
    
    try:
        new_memory = TaskService.manual_add_memory(user_id, content, memory_type)
        return success_response(data=new_memory, code=201)
    except ValueError as e:
        return error_response(message=str(e), code=400)
    except Exception as e:
        return error_response(message=str(e), code=500)

def update_memory(request):
    from ..services.task import TaskService
    
    data = request.get_json()
    if not data or 'id' not in data:
        return error_response(message='缺少记忆 ID', code=400)
    
    memory_id = data['id']
    content = data.get('content')
    memory_type = data.get('type')
    locked = data.get('locked')
    
    if content is None and memory_type is None and locked is None:
        return error_response(message='没有需要更新的内容', code=400)
        
    try:
        updated_memory = TaskService.update_memory(memory_id, content, memory_type, locked)
        return success_response(data=updated_memory)
    except ValueError as e:
        return error_response(message=str(e), code=404)
    except Exception as e:
        return error_response(message=str(e), code=500)

def delete_memory(request):
    from ..services.task import TaskService
    
    data = request.get_json()
    if not data or 'ids' not in data:
        return error_response(message='缺少记忆 ID 列表 (ids)', code=400)
    
    memory_ids = data['ids']
    if not isinstance(memory_ids, list):
        return error_response(message='ids 必须是数组', code=400)
        
    try:
        TaskService.delete_memories(memory_ids)
        return success_response(message='记忆删除成功')
    except ValueError as e:
        return error_response(message=str(e), code=404)
    except Exception as e:
        return error_response(message=str(e), code=500)

def get_memory_types():
    from ..models.memory import MemoryType
    
    type_mapping = {
        MemoryType.POSITION.value: "岗位",
        MemoryType.WORK_CONTENT.value: "工作内容",
        MemoryType.WRITING_PREFERENCE.value: "写作偏好",
        MemoryType.HISTORICAL_CONTEXT.value: "历史对话核心内容"
    }
    
    # Return as list of objects for frontend convenience
    result = [
        {"value": key, "label": value} 
        for key, value in type_mapping.items()
    ]
    
    return success_response(data=result)
