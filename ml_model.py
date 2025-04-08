# ml_model.py
import numpy as np
from sklearn.tree import DecisionTreeClassifier
import pandas as pd
from datetime import datetime

# Dummy dataset for training (can be replaced with real user data later)
data = pd.DataFrame({
    'deadline_hours': [2, 5, 24, 12, 48],
    'estimated_time': [1, 2, 3, 4, 1],
    'importance_level': [5, 4, 2, 1, 3],
    'priority': ['High', 'High', 'Medium', 'Low', 'Medium']
})

X = data[['deadline_hours', 'estimated_time', 'importance_level']]
y = data['priority']

model = DecisionTreeClassifier()
model.fit(X, y)

def predict_priority(task_data):
    try:
        deadline = datetime.strptime(task_data['deadline'], '%Y-%m-%dT%H:%M')
    except:
        return 'Low'

    now = datetime.now()
    delta_hours = (deadline - now).total_seconds() / 3600

    features = np.array([[ 
        delta_hours,
        task_data.get('estimated_time', 1),
        task_data.get('importance_level', 3)
    ]])

    print("📊 Features to model:", features)

    predicted_priority = model.predict(features)[0]
    print("🎯 Predicted:", predicted_priority)
    return predicted_priority
