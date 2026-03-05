from flask import jsonify

def create_task(message):
    from ..services.task import TaskService
    
    task_id = TaskService.create_background_task(message)
    return task_id

def get_task(task_id):
    from ..services.task import TaskService
    
    result = TaskService.get_task_status(task_id)
    return jsonify(result)

def add_memory(request):
    from ..services.task import TaskService
    
    data = request.get_json()
    if not data or 'user_input' not in data or 'user_id' not in data:
        return jsonify({'error': 'Missing user_input or user_id'}), 400
        
    task_id = TaskService.create_memory_task(data['user_input'], data['user_id'])
    return jsonify({'task_id': task_id, 'status': 'running'}), 202

def search_memory(request):
    from ..services.task import TaskService
    
    data = request.get_json()
    if not data or 'user_id' not in data or 'query' not in data:
        return jsonify({'error': 'Missing user_id or query'}), 400
        
    user_id = data['user_id']
    query = data['query']
    top_k = data.get('top_k', 5)
    
    results = TaskService.search_memories(user_id, query, top_k)
    return jsonify(results), 200
