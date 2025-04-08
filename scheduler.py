# ✅ scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

scheduler = BackgroundScheduler()

def check_reminders():
    from models import Reminder, Notification
    from app import db

    now = datetime.utcnow()
    reminders = Reminder.query.filter(Reminder.remind_at <= now, Reminder.is_sent == False).all()

    for reminder in reminders:
        notif = Notification(
            user_id=reminder.user_id,
            message=f"Reminder: {reminder.message}"
        )
        db.session.add(notif)
        reminder.is_sent = True

    db.session.commit()
    print(f"[{datetime.now()}] Checked reminders: {len(reminders)} notifications sent.")

def analyze_daily_log_job():
    from analyze_daily_log import analyze_daily_log
    analyze_daily_log()
    print(f"[{datetime.now()}] Daily log analysis completed.")

scheduler.add_job(func=check_reminders, trigger="interval", seconds=30)
scheduler.add_job(func=analyze_daily_log_job, trigger="cron", hour=23, minute=55)
print("✅ Scheduler initialized and jobs registered.")

def calendar_events_job():
    from calendar_to_task import process_all_events_to_tasks
    process_all_events_to_tasks()
    print(f"[{datetime.now()}] Synced calendar events to tasks.")

scheduler.add_job(func=check_reminders, trigger="interval", seconds=30)
scheduler.add_job(func=analyze_daily_log_job, trigger="cron", hour=23, minute=55)

