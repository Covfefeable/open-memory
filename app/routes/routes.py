from flask import jsonify, request
from . import api_bp
from ..controllers import task

@api_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'})

@api_bp.route('/tasks', methods=['POST'])
def create_task():
    # This might need update if create_task logic moved or changed
    # Assuming basic echo for now or update later
    pass

@api_bp.route('/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    return task.get_task(task_id)

@api_bp.route('/memory/add', methods=['POST'])
def add_memory():
    return task.add_memory(request)
