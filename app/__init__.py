from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from .config import config
from .extensions import db, migrate, celery_init_app

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize Celery configuration
    app.config.from_mapping(
        CELERY=dict(
            broker_url=app.config['CELERY_BROKER_URL'],
            result_backend=app.config['CELERY_RESULT_BACKEND'],
            task_ignore_result=True,
        ),
    )
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    celery_init_app(app)
    
    # Import tasks to ensure they are registered
    from .tasks import background, memory as memory_tasks

    # Import models for migration
    with app.app_context():
        from .models import task, memory

    # Register Blueprints
    from .routes import api_bp
    app.register_blueprint(api_bp)

    return app

def make_celery(app_name=__name__):
    app = create_app()
    return app.extensions["celery"]

celery = make_celery()
