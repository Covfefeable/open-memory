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
        return error_response(message="Task not found", code=404)
    return success_response(data=result)

def add_memory(request):
    from ..services.task import TaskService
    
    data = request.get_json()
    if not data or 'user_input' not in data or 'user_id' not in data or 'llm_output' not in data:
        return error_response(message='Missing user_input, user_id or llm_output', code=400)
        
    task_id = TaskService.create_memory_task(data['user_input'], data['user_id'], data['llm_output'])
    return success_response(data={'task_id': task_id, 'status': 'running'}, code=202)

def search_memory(request):
    from ..services.task import TaskService
    
    data = request.get_json()
    if not data or 'user_id' not in data or 'query' not in data:
        return error_response(message='Missing user_id or query', code=400)
        
    user_id = data['user_id']
    query = data['query']
    top_k = data.get('top_k', 5)
    
    results = TaskService.search_memories(user_id, query, top_k)
    return success_response(data=results)

def list_memory(request):
    from ..services.task import TaskService
    
    data = request.get_json()
    if not data or 'user_id' not in data:
        return error_response(message='Missing user_id', code=400)
        
    user_id = data['user_id']
    memory_type = data.get('type') # Optional
    
    results = TaskService.list_memories(user_id, memory_type)
    return success_response(data=results)

def manual_add_memory(request):
    from ..services.task import TaskService
    
    data = request.get_json()
    if not data or 'user_id' not in data or 'content' not in data:
        return error_response(message='Missing user_id or content', code=400)
    
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
        return error_response(message='Missing memory id', code=400)
    
    memory_id = data['id']
    content = data.get('content')
    memory_type = data.get('type')
    locked = data.get('locked')
    
    if content is None and memory_type is None and locked is None:
        return error_response(message='Nothing to update', code=400)
        
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
    if not data or 'id' not in data:
        return error_response(message='Missing memory id', code=400)
    
    memory_id = data['id']
    try:
        TaskService.delete_memory(memory_id)
        return success_response(message='Memory deleted successfully')
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
