class InterventionEngine:
    """
    AI-Powered Intervention Recommendation Engine
    Generates actionable intervention plans based on a student's risk profile.
    """
    def __init__(self):
        pass
        
    def generate_recommendations(self, risk_level, dominant_factors, data):
        """
        Generates a list of recommended actions.
        risk_level: High, Medium, Low
        dominant_factors: list of factors, e.g. ['Attendance', 'Backlogs']
        data: student feature dictionary (attendance, avg_marks, backlogs, etc.)
        
        Returns:
            list of dict: [{"action": str, "priority": int, "rationale": str, "expected_outcome": str}]
        """
        recommendations = []
        priority_counter = 1
        
        att = data.get('avg_attendance', data.get('attendance', 0))
        mrks = data.get('avg_marks', data.get('marks', 0))
        bkl = data.get('backlogs', 0)
        
        # 1. High Risk Logic
        if risk_level == "High":
            # Mandatory High Risk interventions
            recommendations.append({
                "action": "Parent Meeting & Counseling",
                "priority": priority_counter,
                "rationale": f"Student is at High Risk. Immediate parent engagement is mandatory.",
                "expected_outcome": "Identify root causes of poor performance and establish accountability."
            })
            priority_counter += 1
            
            if 'Attendance' in dominant_factors or att < 65:
                recommendations.append({
                    "action": "Strict Daily Attendance Monitoring",
                    "priority": priority_counter,
                    "rationale": f"Attendance is critically low at {att}%.",
                    "expected_outcome": "Improve attendance to above 75% within 4 weeks."
                })
                priority_counter += 1
                
            if 'Backlogs' in dominant_factors or bkl > 2:
                recommendations.append({
                    "action": "Special Backlog Coaching",
                    "priority": priority_counter,
                    "rationale": f"Student has {bkl} active backlogs threatening degree progression.",
                    "expected_outcome": "Clear at least 50% of backlogs in upcoming supplementary exams."
                })
                priority_counter += 1
                
            if 'Academics' in dominant_factors or mrks < 50:
                recommendations.append({
                    "action": "Mandatory Remedial Classes",
                    "priority": priority_counter,
                    "rationale": f"Overall marks ({mrks}%) indicate severe conceptual gaps.",
                    "expected_outcome": "Improve internal assessment scores by 15%."
                })
                priority_counter += 1
                
        # 2. Medium Risk Logic
        elif risk_level == "Medium":
            recommendations.append({
                "action": "Faculty Mentor Assignment",
                "priority": priority_counter,
                "rationale": "Student is showing signs of academic decline and needs guidance.",
                "expected_outcome": "Provide weekly academic mentoring and course correction."
            })
            priority_counter += 1
            
            if 'Attendance' in dominant_factors or att < 75:
                recommendations.append({
                    "action": "Attendance Warning & Counseling",
                    "priority": priority_counter,
                    "rationale": f"Attendance has dropped to {att}%.",
                    "expected_outcome": "Prevent attendance from falling below the 65% threshold."
                })
                priority_counter += 1
                
            if 'Backlogs' in dominant_factors or bkl > 0:
                recommendations.append({
                    "action": "Academic Advisor Meeting",
                    "priority": priority_counter,
                    "rationale": f"Student has {bkl} backlogs that need addressing.",
                    "expected_outcome": "Create a clear study plan for backlog recovery."
                })
                priority_counter += 1
                
            if 'Academics' in dominant_factors or mrks < 60:
                recommendations.append({
                    "action": "Subject-Specific Tutoring",
                    "priority": priority_counter,
                    "rationale": f"Marks ({mrks}%) show potential weaknesses in core subjects.",
                    "expected_outcome": "Strengthen understanding of difficult topics."
                })
                priority_counter += 1
                
        # 3. Low Risk Logic
        else:
            recommendations.append({
                "action": "Monitor Progress",
                "priority": priority_counter,
                "rationale": "Student is currently performing safely.",
                "expected_outcome": "Maintain current academic trajectory."
            })
            priority_counter += 1
            
            if att < 85:
                recommendations.append({
                    "action": "Encourage Participation",
                    "priority": priority_counter,
                    "rationale": "While safe, attendance could be improved.",
                    "expected_outcome": "Increase active engagement in classes."
                })
                priority_counter += 1
                
        return recommendations

    def generate_nlp_report(self, risk_level, dominant_factors, data, recommendations):
        """
        Generates a natural language summary of the risk profile and recommended actions.
        """
        att = data.get('avg_attendance', data.get('attendance', 0))
        mrks = data.get('avg_marks', data.get('marks', 0))
        bkl = data.get('backlogs', 0)
        is_first_year = '1' in str(data.get('year', '')).lower() or 'first' in str(data.get('year', '')).lower()
        
        # Format factors nicely
        formatted_factors = []
        for f in dominant_factors:
            f = f.lower()
            if 'attendance' in f: formatted_factors.append("declining attendance")
            elif 'backlog' in f: formatted_factors.append("an increasing backlog count")
            elif 'mark' in f or 'exam' in f or 'academic' in f or 'performance' in f: formatted_factors.append("weak performance in recent assessments")
            elif 'leave' in f or 'absences' in f: formatted_factors.append("frequent consecutive absences")
            else: formatted_factors.append(f.replace('_', ' '))
            
        factor_str = " and ".join(formatted_factors) if len(formatted_factors) <= 2 else ", ".join(formatted_factors[:-1]) + ", and " + formatted_factors[-1]
        if not factor_str: factor_str = "general academic indicators"
        
        if risk_level == "High":
            report = f"This student has been classified as High Risk due to {factor_str}. Immediate academic intervention is recommended to prevent further decline."
        elif risk_level == "Medium":
            report = f"This student is currently classified as Medium Risk. Early indicators point to {factor_str}. Preventative intervention is recommended to correct the trajectory before it impacts their degree progression."
        else:
            report = "This student currently demonstrates stable academic performance. Strong attendance levels and consistent academic scores contribute positively to the overall risk assessment."
            
        if is_first_year and risk_level != "Low":
            report += " Since this is a first-year student, this assessment heavily factors in their high school/diploma foundations alongside early semester indicators."

        if recommendations:
            actions = [r['action'] for r in recommendations]
            report += " The AI specifically prescribes: "
            if len(actions) > 1:
                report += ", ".join(actions[:-1]) + " and " + actions[-1] + "."
            else:
                report += actions[0] + "."
                
        return report

    def get_database_interventions(self, college_name, student_id):
        """
        Fetches previously saved interventions for a student from the central DB.
        """
        from logic.central_auth import CentralAuth
        conn = CentralAuth()._get_conn()
        if not conn:
            return []
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM interventions WHERE college_name=%s AND student_id=%s ORDER BY priority ASC",
                (college_name, student_id)
            )
            return cursor.fetchall()
        except Exception as e:
            print(f"Error fetching interventions: {e}")
            return []
        finally:
            conn.close()

    def save_intervention(self, college_name, student_id, faculty_username, risk_level, dominant_factor, action, priority, status="Planned"):
        """
        Saves a new intervention tracking record.
        """
        from logic.central_auth import CentralAuth
        conn = CentralAuth()._get_conn()
        if not conn:
            return False
        try:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO interventions 
                   (college_name, student_id, faculty_username, risk_level, dominant_factor, recommended_action, priority, status)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (college_name, student_id, faculty_username, risk_level, dominant_factor, action, priority, status)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving intervention: {e}")
            return False
        finally:
            conn.close()
            
    def update_intervention_status(self, record_id, new_status):
        """
        Updates the status of an existing intervention.
        """
        from logic.central_auth import CentralAuth
        conn = CentralAuth()._get_conn()
        if not conn:
            return False
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE interventions SET status=%s WHERE id=%s", (new_status, record_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating intervention: {e}")
            return False
        finally:
            conn.close()

    def calculate_effectiveness(self, student_history):
        # Calculates intervention effectiveness based on pre and post semester comparisons
        if not student_history or len(student_history) < 2:
            return {'status': 'Insufficient Data', 'score': 0, 'attendance_diff': 0, 'marks_diff': 0, 'backlog_diff': 0}
            
        hist = sorted(student_history, key=lambda x: x.get('semester', 0))
        pre = hist[-2]
        post = hist[-1]
        
        att_diff = post.get('attendance', 0) - pre.get('attendance', 0)
        # cgpa is out of 10, marks out of 100
        mrk_diff = (post.get('cgpa', 0) * 10) - (pre.get('cgpa', 0) * 10)
        bkl_diff = pre.get('backlogs', 0) - post.get('backlogs', 0) # Positive is good (cleared backlogs)
        
        score = 0
        if att_diff > 0: score += 30
        if mrk_diff > 0: score += 40
        if bkl_diff > 0: score += 30
        
        if score > 70: status = 'Highly Successful'
        elif score > 30: status = 'Moderately Successful'
        else: status = 'Ineffective'
        
        return {
            'status': status,
            'score': score,
            'attendance_diff': round(att_diff, 1),
            'marks_diff': round(mrk_diff, 1),
            'backlog_diff': bkl_diff
        }
