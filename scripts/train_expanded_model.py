import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib
import mysql.connector
import json
import os

def fetch_data():
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from logic.config_manager import load_config
    from logic.db_handler import DBHandler
    
    all_cfg = load_config()
    config = all_cfg.get('erp', {})
    central_config = all_cfg.get('central', {})
    
    # Connect to central DB to get the schema map
    try:
        c_conn = mysql.connector.connect(**central_config)
        c_cursor = c_conn.cursor(dictionary=True)
        c_cursor.execute("SELECT * FROM erp_configs WHERE college_name=%s", ("Vishnu",))
        schema_map = c_cursor.fetchone()
        c_conn.close()
        
        if schema_map:
            config.update(schema_map)
    except Exception as e:
        print(f"⚠️ Warning: Could not fetch ERP config from central DB: {e}")
    
    db = DBHandler(config)
    data = db.get_training_data()
    db.close()
    
    return pd.DataFrame(data)

def train_model():
    print("Fetching expanded features from ERP database...")
    df = fetch_data()
    print(f"Loaded {len(df)} academic records.")
    
    # Generate Ground Truth Labels based on a strict set of rules
    conditions = [
        (df['avg_attendance'] < 65) | (df['backlogs'] >= 3) | (df['cgpa'] < 5.0) | (df['consecutive_absences'] >= 5),
        (df['avg_attendance'] < 75) | (df['backlogs'] >= 1) | (df['cgpa'] < 6.5) | (df['consecutive_absences'] >= 3) | (df['avg_marks'] < 50)
    ]
    choices = ['High', 'Medium']
    df['risk'] = np.select(conditions, choices, default='Low')
    
    print(f"Label distribution:\n{df['risk'].value_counts()}")
    
    X = df.drop('risk', axis=1)
    y = df['risk']
    
    # Handle missing values if any
    X = X.fillna(X.mean())
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("Training Random Forest Classifier on 12 features...")
    model = RandomForestClassifier(n_estimators=100, max_depth=7, random_state=42)
    model.fit(X_train, y_train)
    
    print("Evaluation:")
    print(classification_report(y_test, model.predict(X_test)))
    
    # Assign the expected columns so predictor can verify them later if needed
    model.feature_names_in_ = X.columns.to_numpy()
    
    model_path = os.path.join(os.path.dirname(__file__), '..', 'synapse_model.pkl')
    joblib.dump(model, model_path)
    
    # Save the expected feature names for the dynamic schema mapper
    features_path = os.path.join(os.path.dirname(__file__), '..', 'synapse_model.features.json')
    with open(features_path, 'w') as f:
        json.dump(list(X.columns), f)
        
    print(f"Saved highly advanced synapse_model.pkl to {model_path} successfully!")
    print(f"Saved required features to {features_path} successfully!")

if __name__ == "__main__":
    train_model()
