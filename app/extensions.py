from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from celery import Celery, Task

db = SQLAlchemy()
migrate = Migrate()

def celery_init_app(app):
    class FlaskTask(Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object(app.config["CELERY"])
    
    # Configure periodic tasks
    celery_app.conf.beat_schedule = {
        'compress-memories-every-5-minutes': {
            'task': 'app.tasks.background.compress_user_memories',
            'schedule': 300.0, # 5 minutes
        },
    }
    
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    return celery_app
