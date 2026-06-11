import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib

def generate_first_year_data(num_samples=2000):
    np.random.seed(42)
    
    tenth = np.random.normal(75, 12, num_samples)
    higher_edu = np.random.normal(70, 15, num_samples)
    attendance = np.random.normal(80, 15, num_samples)
    internal_marks = np.random.normal(65, 18, num_samples)
    absences = np.random.poisson(2, num_samples)
    
    # Clip values to valid ranges
    tenth = np.clip(tenth, 35, 100)
    higher_edu = np.clip(higher_edu, 35, 100)
    attendance = np.clip(attendance, 10, 100)
    internal_marks = np.clip(internal_marks, 0, 100)
    absences = np.clip(absences, 0, 30)
    
    data = pd.DataFrame({
        'tenth_percentage': tenth,
        'prior_higher_edu_percentage': higher_edu,
        'attendance': attendance,
        'internal_marks': internal_marks,
        'consecutive_absences': absences
    })
    
    # Define Ground Truth Rules
    conditions = [
        (data['attendance'] < 65) | ((data['tenth_percentage'] < 55) & (data['prior_higher_edu_percentage'] < 55)),
        (data['attendance'] < 75) | (data['internal_marks'] < 50) | (data['consecutive_absences'] > 5)
    ]
    choices = ['High', 'Medium']
    data['risk'] = np.select(conditions, choices, default='Low')
    
    return data

def train_model():
    print("Generating synthetic first-year data...")
    df = generate_first_year_data(5000)
    
    X = df.drop('risk', axis=1)
    y = df['risk']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("Training Random Forest Classifier...")
    model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    model.fit(X_train, y_train)
    
    print("Evaluation:")
    print(classification_report(y_test, model.predict(X_test)))
    
    joblib.dump(model, 'first_year_model.pkl')
    print("Saved first_year_model.pkl successfully!")

if __name__ == "__main__":
    train_model()
