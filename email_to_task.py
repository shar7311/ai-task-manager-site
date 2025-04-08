import re
import logging
import dateparser
from datetime import datetime
from task_utils import create_task_from_data

# Configure logging
logging.basicConfig(level=logging.INFO)

# Extended keywords for better task detection
TASK_KEYWORDS = [
    "submit", "attend", "complete", "pay", "join", "upload",
    "deadline", "reminder", "exam", "meeting", "assignment", "task"
]

def extract_task_from_email(subject, body):
    full_text = subject + " " + body

    # Find first matching keyword
    found_keyword = next((kw for kw in TASK_KEYWORDS if kw in full_text.lower()), None)
    if not found_keyword:
        logging.debug("No task keyword found in email.")
        return None

    # Parse due date/time from natural language
    due_time = dateparser.parse(full_text, settings={'PREFER_DATES_FROM': 'future'})

    # Get relevant sentence for the task title
    sentences = re.split(r'[.?!]', full_text)
    task_sentence = next((s for s in sentences if found_keyword in s.lower()), subject)

    return {
        "title": task_sentence.strip().capitalize(),
        "due_time": due_time.strftime('%Y-%m-%d %H:%M:%S') if due_time else None,
        "source": "email"
    }

def process_email_to_task(subject, body):
    task_info = extract_task_from_email(subject, body)
    
    if task_info and task_info['due_time']:
        task_data = {
            'title': task_info['title'],
            'description': body,
            'deadline': task_info['due_time'],
            'estimated_time': 1,  # You can later replace this with NLP-based estimates
            'importance_level': 3,
            'category': 'Email'
        }
        
        create_task_from_data(task_data)
        logging.info(f"[Task Created] {task_data['title']} | Due: {task_data['deadline']}")
        return task_data
    else:
        logging.warning("Email did not contain valid task or due time.")
        return None
