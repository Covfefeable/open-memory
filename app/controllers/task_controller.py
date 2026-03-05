from flask import jsonify

def create_task(request):
    from ..services.task_service import TaskService
    
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'error': 'Missing message'}), 400
        
    task_id = TaskService.create_background_task(data['message'])
    return jsonify({'task_id': task_id, 'status': 'submitted'}), 202

def get_task(task_id):
    from ..services.task_service import TaskService
    
    result = TaskService.get_task_status(task_id)
    return jsonify(result)
