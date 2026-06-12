import sys
import os

# Ensure the logic module can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic.central_auth import CentralAuth
from logic.db_handler import DBHandler
from logic.predictor import RiskPredictor
from logic.email_service import EmailService
from logic.encryption import decrypt_text

def run_scanner():
    print("Starting Early Warning Scanner...")
    
    ca = CentralAuth()
    conn = ca._get_conn()
    if not conn:
        print("Failed to connect to Central Auth DB.")
        return
        
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM erp_configs")
        configs = cursor.fetchall()
    except Exception as e:
        print("Failed to fetch configs:", e)
        return
    finally:
        conn.close()
        
    predictor = RiskPredictor()
    email_service = EmailService()
    
    for erp in configs:
        college = erp['college_name']
        print(f"\nScanning College: {college}")
        
        # Build the config dictionary as expected by DBHandler
        config = {
            "db_type": erp['db_type'], "host": erp['db_host'], "port": erp['db_port'],
            "user": erp['db_user'], "password": decrypt_text(erp['encrypted_pass']),
            "database": erp['db_name']
        }
        for k, v in erp.items():
            if k.startswith('tbl_') or k.startswith('col_'):
                if v is not None:
                    config[k] = v
                    
        db = DBHandler(config)
        students = db.get_all_students()
        
        print(f"Found {len(students)} students in {college}. Analyzing...")
        
        for student in students:
            student_id = str(student.get("registration_no", student.get("display_reg_no", student.get("id", ""))))
            if not student_id:
                continue
                
            history = student.get("history", [])
            if not history:
                # Fetch history manually
                history = db.get_student_history(student_id)
                student["history"] = history
                
            if not history:
                continue # Cannot detect a jump without history
                
            # Current semester data
            current_data = student
            # We assume current_data contains the latest semester info
            current_sem = current_data.get('year', 'Unknown')
            
            # Predict current risk
            current_report = predictor.analyze_student(current_data, current_sem=current_sem, history_data=history)
            curr_level = current_report.get("level", "Low")
            
            # Identify sudden jump
            jump_detected = False
            
            # 1. TrendAnalyzer check
            trend_info = current_report.get("trend_info")
            if trend_info and trend_info.get("is_critical_drop"):
                jump_detected = True
                
            # 2. Manual previous semester check
            if not jump_detected and len(history) >= 2:
                # History is usually sorted. Let's get the second to last (previous) if the last is current.
                sorted_hist = sorted(history, key=lambda x: x.get('semester', 0))
                if len(sorted_hist) >= 2:
                    prev_data = sorted_hist[-2] # Current is usually [-1]
                    prev_hist = sorted_hist[:-1]
                    prev_report = predictor.analyze_student(prev_data, current_sem=prev_data.get('semester', 'Unknown'), history_data=prev_hist)
                    prev_level = prev_report.get("level", "Low")
                    
                    if prev_level in ["Low", "Medium"] and curr_level == "High":
                        jump_detected = True
                        
            if jump_detected and curr_level == "High":
                # Ensure we haven't already sent an alert for this student this semester
                alert_type = "Sudden_High_Risk_Jump"
                
                # Check email logs
                if ca.check_email_sent(college, student_id, alert_type, current_sem):
                    # Already sent
                    continue
                    
                student_email = student.get("email", "")
                parent_email = student.get("parent_email", "")
                
                emails_to_send = []
                if student_email: emails_to_send.append(student_email)
                if parent_email: emails_to_send.append(parent_email)
                
                if not emails_to_send:
                    print(f"[{student_id}] Jump detected but NO emails found on record.")
                    continue
                    
                student_name = student.get("name", student_id)
                dom_factor = current_report.get("dominant", "Unknown Factor")
                
                print(f"[{student_id}] SUDDEN JUMP DETECTED -> Sending Email to {emails_to_send}...")
                
                success = email_service.send_early_warning_alert(
                    to_emails=emails_to_send,
                    student_name=student_name,
                    student_id=student_id,
                    college_name=college,
                    risk_level=curr_level,
                    dominant_factor=dom_factor
                )
                
                if success:
                    ca.log_email_sent(college, student_id, alert_type, current_sem)

if __name__ == "__main__":
    run_scanner()
