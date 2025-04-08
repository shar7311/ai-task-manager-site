# task_utils.py
from models import Task
from ml_model import predict_priority
from extensions import db
from datetime import datetime

def create_task_from_data(data):
    # Required: title, deadline (string), estimated_time, importance_level
    deadline_str = data.get('deadline')
    try:
        deadline_obj = datetime.strptime(deadline_str, '%Y-%m-%d %H:%M:%S')
    except:
        deadline_obj = datetime.now()  # fallback

    # Predict the priority
    predicted_priority = predict_priority({
        'deadline': deadline_str,
        'estimated_time': data.get('estimated_time', 1),
        'importance_level': data.get('importance_level', 3)
    })

    new_task = Task(
        title=data.get('title'),
        description=data.get('description'),
        due_date=deadline_obj,
        deadline=deadline_obj,
        estimated_time=str(data.get('estimated_time', 1)),
        importance_level=str(data.get('importance_level', 3)),
        priority=predicted_priority,
        status='pending',
        category=data.get('category', 'General')
    )

    db.session.add(new_task)
    db.session.commit()
    return new_task
