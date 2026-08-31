class AdaptiveLabelGenerator:
    def __init__(self, marking_scheme: dict):
        self.scheme = marking_scheme

    def generate_labels(self, student_records: list[dict]) -> list[str]:
        """
        Generate High/Medium/Low risk labels for each student record using the 
        detected scheme's pass thresholds rather than hardcoded values.
        """
        labels = []
        for record in student_records:
            high_count = 0
            med_count = 0
            
            # ATTENDANCE RISK
            if 'attendance_pct' in record and record['attendance_pct'] is not None and 'attendance_pct' in self.scheme:
                att = float(record['attendance_pct'])
                danger_threshold = self.scheme['attendance_pct'].get('danger_threshold', 75.0)
                if att < (danger_threshold * 0.87):
                    high_count += 1
                elif att < danger_threshold:
                    med_count += 1
                    
            # MARKS RISK
            if 'internal_marks' in record and record['internal_marks'] is not None and 'internal_marks' in self.scheme:
                marks = float(record['internal_marks'])
                # Normalize to percentage
                norm_marks = self._normalize_to_percentage(marks, self.scheme['internal_marks'])
                if norm_marks < 40.0:
                    high_count += 1
                elif norm_marks < 55.0:
                    med_count += 1
                    
            # BACKLOG RISK
            if 'backlogs' in record and record['backlogs'] is not None:
                backlogs = int(record['backlogs'])
                if backlogs >= 3:
                    high_count += 1
                elif backlogs >= 1:
                    med_count += 1
                    
            # CGPA RISK
            if 'cgpa' in record and record['cgpa'] is not None and 'cgpa' in self.scheme:
                cgpa = float(record['cgpa'])
                # Normalize to 10-point scale
                norm_pct = self._normalize_to_percentage(cgpa, self.scheme['cgpa'])
                cgpa_10pt = (norm_pct / 100.0) * 10.0
                
                if cgpa_10pt < 5.0:
                    high_count += 1
                elif cgpa_10pt < 6.5:
                    med_count += 1
                    
            # FINAL LABEL
            if high_count > 0:
                labels.append("High")
            elif med_count >= 1: # Prompt says: Elif 2+ dimensions are MEDIUM: label = "Medium". Elif 1 dimension is MEDIUM: label = "Medium".
                labels.append("Medium")
            else:
                labels.append("Low")
                
        return labels

    def generate_from_history(self, semester_records: list[dict]) -> list[str]:
        """
        Enhanced label generation using multi-semester history.
        Assumes `semester_records` are grouped per student in chronological order,
        or we generate a label for a single student given their chronological records.
        If it receives a list of records for a single student, it returns a single list
        with one label (to match the list[str] signature).
        """
        if not semester_records:
            return []
            
        # First generate the base label for the most recent semester
        latest_record = semester_records[-1]
        base_label = self.generate_labels([latest_record])[0]
        
        if len(semester_records) < 2:
            return [base_label]
            
        # Evaluate trend across last few semesters
        # We look at 'internal_marks' or 'cgpa' as the primary indicator of performance
        performance_trend = []
        for rec in semester_records:
            score = 0.0
            if 'internal_marks' in rec and rec['internal_marks'] is not None and 'internal_marks' in self.scheme:
                score = self._normalize_to_percentage(float(rec['internal_marks']), self.scheme['internal_marks'])
            elif 'cgpa' in rec and rec['cgpa'] is not None and 'cgpa' in self.scheme:
                score = self._normalize_to_percentage(float(rec['cgpa']), self.scheme['cgpa'])
            performance_trend.append(score)
            
        if len(performance_trend) >= 2:
            # Check for consecutive declines
            declines = sum(1 for i in range(1, len(performance_trend)) if performance_trend[i] < performance_trend[i-1] - 5.0) # 5% drop
            improvements = sum(1 for i in range(1, len(performance_trend)) if performance_trend[i] > performance_trend[i-1] + 5.0)
            
            label_tiers = ["Low", "Medium", "High"]
            current_tier = label_tiers.index(base_label)
            
            if declines >= 2:
                # Upgrade risk
                current_tier = min(len(label_tiers) - 1, current_tier + 1)
            elif improvements >= 2:
                # Downgrade risk
                current_tier = max(0, current_tier - 1)
                
            base_label = label_tiers[current_tier]
            
        return [base_label]
        
    def _normalize_to_percentage(self, value: float, col_scheme: dict) -> float:
        if not col_scheme or "detected_max" not in col_scheme or col_scheme["detected_max"] == 0:
            return 0.0
        norm = (value / col_scheme["detected_max"]) * 100.0
        return max(0.0, min(100.0, norm))
