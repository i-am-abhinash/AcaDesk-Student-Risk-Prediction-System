# train_model.py
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib

print("🧠 SYNAPSE: Training Random Forest Model...")

# 1. GENERATE SYNTHETIC DATA (The "Textbook" for the AI)
# We create 2000 fake students with patterns to teach the model.
np.random.seed(42)
n_samples = 2000

# Random features
attendance = np.random.randint(40, 100, n_samples)
internal_marks = np.random.randint(20, 100, n_samples)
backlogs = np.random.choice([0, 1, 2, 3, 4, 5], n_samples, p=[0.6, 0.2, 0.1, 0.05, 0.03, 0.02])

# Define the "Ground Truth" Logic (Teaching the model what is Risky)
risk_levels = []
for i in range(n_samples):
    att = attendance[i]
    mrk = internal_marks[i]
    bkl = backlogs[i]
    
    # Logic we want the AI to learn:
    if bkl > 2 or att < 60:
        risk_levels.append("High")
    elif bkl > 0 or att < 75 or mrk < 45:
        risk_levels.append("Medium")
    else:
        risk_levels.append("Low")

# Create DataFrame
df = pd.DataFrame({
    'attendance': attendance,
    'marks': internal_marks,
    'backlogs': backlogs,
    'risk': risk_levels
})

# 2. PREPARE FOR TRAINING
X = df[['attendance', 'marks', 'backlogs']]
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

print(f"✅ Training Complete. Model Accuracy: {model.score(X_test, y_test)*100:.2f}%")
print("💾 Saved to 'synapse_model.pkl'")