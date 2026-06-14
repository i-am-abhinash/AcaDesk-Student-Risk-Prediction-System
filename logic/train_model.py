# train_model.py
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib

print("SYNAPSE: Training Random Forest Model...")

# 1. GENERATE SYNTHETIC DATA (The "Textbook" for the AI)
# We create 2000 fake students with patterns to teach the model.
np.random.seed(42)
n_samples = 2000

# Random features (pessimistic)
attendance = np.random.randint(20, 85, n_samples)
marks = np.random.randint(20, 75, n_samples)
backlogs = np.random.choice([0, 1, 2, 3, 4, 5, 6, 7], n_samples, p=[0.1, 0.1, 0.15, 0.2, 0.2, 0.1, 0.1, 0.05])

# New features
cgpa = marks / 10.0 + np.random.uniform(-0.5, 0.5, n_samples)
mid_exam_score = marks + np.random.randint(-10, 10, n_samples)
lab_performance = marks + np.random.randint(-15, 15, n_samples)
assignment_marks = marks + np.random.randint(-5, 5, n_samples)

tenth = np.random.randint(50, 100, n_samples)
inter = tenth + np.random.randint(-10, 10, n_samples)
diploma = np.where(np.random.rand(n_samples) < 0.1, np.random.randint(50, 90, n_samples), 0)

consecutive_absences = np.where(attendance < 70, np.random.randint(3, 10, n_samples), np.random.randint(0, 3, n_samples))
leave_frequency = np.where(attendance < 80, np.random.randint(2, 8, n_samples), np.random.randint(0, 2, n_samples))

# Define the "Ground Truth" Logic (Teaching the model what is Risky)
risk_levels = []
for i in range(n_samples):
    att = attendance[i]
    mrk = marks[i]
    bkl = backlogs[i]
    cons_abs = consecutive_absences[i]
    leave_freq = leave_frequency[i]
    lab = lab_performance[i]
    mid = mid_exam_score[i]
    c_gpa = cgpa[i]
    t = tenth[i]
    
    # Calculate a composite risk score (0 to 100)
    risk_score = 0
    if bkl > 2: risk_score += 40
    elif bkl > 0: risk_score += 15
    
    if att < 60: risk_score += 30
    elif att < 75: risk_score += 15
    
    if c_gpa < 5.0: risk_score += 20
    elif c_gpa < 6.5: risk_score += 10
    
    if cons_abs > 5: risk_score += 15
    if leave_freq > 4: risk_score += 10
    
    if lab < 50: risk_score += 10
    if mid < 50: risk_score += 10
    
    if t < 60: risk_score += 5
    
    if risk_score >= 50:
        risk_levels.append("High")
    elif risk_score >= 25:
        risk_levels.append("Medium")
    else:
        risk_levels.append("Low")

# Create DataFrame matching exactly predictor.py expected cols
df = pd.DataFrame({
    'avg_attendance': attendance,
    'cgpa': cgpa,
    'backlogs': backlogs,
    'avg_marks': marks,
    'mid_exam_score': mid_exam_score,
    'lab_performance': lab_performance,
    'assignment_marks': assignment_marks,
    'tenth': tenth,
    'inter': inter,
    'diploma': diploma,
    'consecutive_absences': consecutive_absences,
    'leave_frequency': leave_frequency,
    'risk': risk_levels
})

# 2. PREPARE FOR TRAINING
cols = ['avg_attendance', 'cgpa', 'backlogs', 'avg_marks', 
        'mid_exam_score', 'lab_performance', 'assignment_marks',
        'tenth', 'inter', 'diploma', 
        'consecutive_absences', 'leave_frequency']
X = df[cols]
y = df['risk']

# Split into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# 3. TRAIN RANDOM FOREST
# n_estimators=100 means we use 100 Decision Trees voting together
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# 4. SAVE THE BRAIN
# We save the model to a file so the main app can load it instantly
joblib.dump(model, 'synapse_model.pkl')

print(f"Training Complete. Model Accuracy: {model.score(X_test, y_test)*100:.2f}%")
print("Saved to `synapse_model.pkl`.")