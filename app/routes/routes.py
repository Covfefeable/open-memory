from flask import jsonify, request
from . import api_bp
from ..controllers import task_controller

@api_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'})

@api_bp.route('/tasks', methods=['POST'])
def create_task():
    return task_controller.create_task(request)

@api_bp.route('/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    return task_controller.get_task(task_id)
