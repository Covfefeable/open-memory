from flask import jsonify, request
from . import api_bp
from ..controllers import task
from ..utils.response import success_response

@api_bp.route('/health', methods=['GET'])
def health_check():
    return success_response(data={'status': 'ok'})

@api_bp.route('/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    return task.get_task(task_id)

@api_bp.route('/memory/add', methods=['POST'])
def add_memory():
    return task.add_memory(request)

@api_bp.route('/memory/search', methods=['POST'])
def search_memory():
    return task.search_memory(request)

@api_bp.route('/memory/list', methods=['POST'])
def list_memory():
    return task.list_memory(request)

@api_bp.route('/memory/manual_add', methods=['POST'])
def manual_add_memory():
    return task.manual_add_memory(request)

@api_bp.route('/memory/update', methods=['POST'])
def update_memory():
    return task.update_memory(request)

@api_bp.route('/memory/delete', methods=['POST'])
def delete_memory():
    return task.delete_memory(request)
