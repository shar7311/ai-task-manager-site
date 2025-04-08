# calendar_to_task.py
from models import CalendarEvent, Task
from ml_model import predict_priority
from extensions import db
from datetime import datetime

def convert_event_to_task(event):
    title = event.title
    description = event.description or ""
    deadline = event.start_time

    task_data = {
        'title': title,
        'description': description,
        'deadline': deadline.strftime('%Y-%m-%d %H:%M'),
        'estimated_time': 1,  # Default for now, can be improved later
        'importance_level': 3  # Neutral by default
    }

    priority_str = predict_priority(task_data)
    priority_map = {'Low': 1, 'Medium': 2, 'High': 3}
    priority = priority_map.get(priority_str, 2)

    new_task = Task(
        title=title,
        description=description,
        due_date=deadline,
        deadline=deadline,
        estimated_time='1',
        importance_level='3',
        priority=priority,
        status='Pending',
        category='Calendar'
    )
    return new_task

def process_all_events_to_tasks():
    events = CalendarEvent.query.all()
    for event in events:
        # Skip if task with same title and deadline already exists
        existing = Task.query.filter_by(title=event.title, deadline=event.start_time).first()
        if existing:
            continue
        task = convert_event_to_task(event)
        db.session.add(task)

    db.session.commit()
    print("All events converted to tasks.")
