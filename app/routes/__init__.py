from flask import Blueprint, request, jsonify, current_app
from functools import wraps
from ..utils.response import error_response

api_bp = Blueprint('api', __name__, url_prefix='/api')

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Skip auth for health check
        if request.endpoint and 'health' in request.endpoint:
            return f(*args, **kwargs)
            
        token = request.headers.get('Authorization')
        expected_token = current_app.config.get('API_AUTH_TOKEN')
        
        # If no token configured on server, allow access (or default to secure deny?)
        # Let's secure deny if configured
        if expected_token:
            if not token:
                return error_response(message='Missing Authorization header', code=401)
            
            # Support "Bearer <token>" format
            if token.startswith('Bearer '):
                token = token.split(' ')[1]
                
            if token != expected_token:
                return error_response(message='Invalid token', code=401)
                
        return f(*args, **kwargs)
    return decorated

# Apply auth globally to the blueprint
@api_bp.before_request
def before_request():
    # We can't use the decorator on before_request easily to stop execution,
    # but we can call the logic directly.
    # However, before_request doesn't support the decorator pattern nicely for return values.
    # So we'll implement the logic here directly.
    
    # Skip auth for health check (using endpoint name)
    if request.endpoint and 'health' in request.endpoint:
        return None
        
    # Skip for OPTIONS requests (CORS preflight)
    if request.method == 'OPTIONS':
        return None
        
    token = request.headers.get('Authorization')
    expected_token = current_app.config.get('API_AUTH_TOKEN')
    
    if expected_token:
        if not token:
            return error_response(message='Missing Authorization header', code=401)
        
        if token.startswith('Bearer '):
            token = token.split(' ')[1]
            
        if token != expected_token:
            return error_response(message='Invalid token', code=401)

from . import routes
