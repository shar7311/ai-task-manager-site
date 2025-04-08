# analyze_daily_log.py
from datetime import datetime, timedelta
from models import Task, CalendarEvent, DailyLog
from extensions import db

def analyze_daily_log(date=None):
    if not date:
        date = datetime.utcnow().date()

    start = datetime.combine(date, datetime.min.time())
    end = datetime.combine(date, datetime.max.time())

    # Fetch tasks and events of the day
    tasks = Task.query.filter(Task.due_date >= start, Task.due_date <= end).all()
    events = CalendarEvent.query.filter(CalendarEvent.start_time >= start, CalendarEvent.start_time <= end).all()

    total_task_time = 0
    wasted_task_time = 0

    for task in tasks:
        est_time = int(task.estimated_time) if task.estimated_time else 1
        priority = int(task.priority) if task.priority else 3
        total_task_time += est_time
        if priority <= 2:  # Low priority
            wasted_task_time += est_time

    # Calculate calendar event time
    event_time = sum([(e.end_time - e.start_time).seconds // 3600 for e in events])

    total_time_spent = total_task_time + event_time
    wasted_percentage = (wasted_task_time / total_task_time) * 100 if total_task_time else 0

    log_content = (
        f"Date: {date}\n"
        f"Total productive time: {total_time_spent} hours\n"
        f"Low-priority task time: {wasted_task_time} hours\n"
        f"Wasted time % (based on tasks): {wasted_percentage:.2f}%\n"
        f"Calendar Events: {len(events)} events\n"
        f"Tasks: {len(tasks)} tasks"
    )

    daily_log = DailyLog(date=date, content=log_content)
    db.session.add(daily_log)
    db.session.commit()

    print("[DailyLog] Analysis completed and saved.")
