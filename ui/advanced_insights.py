import customtkinter as ctk
import pandas as pd
import numpy as np
import joblib
import os
import threading
from tkinter import Canvas
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, roc_curve, auc
from sklearn.preprocessing import label_binarize

class AdvancedInsightsPanel(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, corner_radius=0, fg_color="#121212")
        self.controller = controller
        
        # Header
        self.header = ctk.CTkFrame(self, fg_color="#1e1e1e", height=60, corner_radius=0)
        self.header.pack(fill="x", side="top")
        self.header.pack_propagate(False)
        ctk.CTkLabel(self.header, text="✨ AI Model Evaluation Dashboard", font=("Arial", 24, "bold"), text_color="#00E5FF").pack(side="left", padx=20)
        
        # Main content area
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.model = None
        self.model_features = []
        self.metrics_data = {}
        
        self.loading_lbl = ctk.CTkLabel(self.scroll, text="Loading AI Model and Evaluating Performance...", font=("Arial", 16))
        self.loading_lbl.pack(pady=50)

    def refresh(self):
        # Trigger evaluation in a thread to keep UI responsive
        for widget in self.scroll.winfo_children():
            widget.destroy()
        
        self.loading_lbl = ctk.CTkLabel(self.scroll, text="Evaluating SYNAPSE AI Model Performance...", font=("Arial", 16, "italic"), text_color="#aaaaaa")
        self.loading_lbl.pack(pady=50)
        
        t = threading.Thread(target=self._run_evaluation)
        t.start()

    def _run_evaluation(self):
        try:
            model_path = "synapse_model.pkl"
            if not os.path.exists(model_path):
                model_path = os.path.join("..", "synapse_model.pkl")
            
            if os.path.exists(model_path):
                self.model = joblib.load(model_path)
            else:
                self.after(0, self._show_error, "Model file not found. Please train the model first.")
                return

            if hasattr(self.model, 'feature_names_in_'):
                self.model_features = list(self.model.feature_names_in_)
            else:
                self.model_features = ['attendance', 'marks', 'backlogs'] # Fallback
                
            # Generate synthetic validation set based on expected features
            n_samples = 1000
            np.random.seed(99)
            X_dict = {}
            for f in self.model_features:
                if 'att' in f: X_dict[f] = np.random.randint(40, 100, n_samples)
                elif 'mark' in f: X_dict[f] = np.random.randint(20, 100, n_samples)
                elif 'backlog' in f: X_dict[f] = np.random.choice([0, 1, 2, 3, 4], n_samples, p=[0.6, 0.2, 0.1, 0.05, 0.05])
                else: X_dict[f] = np.random.randint(0, 100, n_samples)
            
            X_test = pd.DataFrame(X_dict)
            
            # Ground truth generation (following train_model logic)
            y_true = []
            for i in range(n_samples):
                att = X_dict.get('attendance', X_dict.get('avg_attendance', 70))[i]
                mrk = X_dict.get('marks', X_dict.get('avg_marks', 60))[i]
                bkl = X_dict.get('backlogs', 0)[i]
                
                if bkl > 2 or att < 60: y_true.append("High")
                elif bkl > 0 or att < 75 or mrk < 45: y_true.append("Medium")
                else: y_true.append("Low")
                
            y_true = np.array(y_true)
            
            # Predictions
            y_pred = self.model.predict(X_test)
            y_probs = self.model.predict_proba(X_test)
            
            # Compute Metrics
            acc = accuracy_score(y_true, y_pred)
            prec = precision_score(y_true, y_pred, average='weighted', zero_division=0)
            rec = recall_score(y_true, y_pred, average='weighted', zero_division=0)
            f1 = f1_score(y_true, y_pred, average='weighted', zero_division=0)
            cm = confusion_matrix(y_true, y_pred, labels=["High", "Medium", "Low"])
            
            # Feature Importances
            importances = []
            if hasattr(self.model, 'feature_importances_'):
                importances = self.model.feature_importances_
            
            self.metrics_data = {
                "accuracy": acc, "precision": prec, "recall": rec, "f1": f1,
                "confusion_matrix": cm, "y_true": y_true, "y_probs": y_probs,
                "importances": importances
            }
            
            if hasattr(self, 'winfo_exists') and self.winfo_exists():
                self.after(0, self._render_dashboard)
            
        except Exception as e:
            if hasattr(self, 'winfo_exists') and self.winfo_exists():
                self.after(0, self._show_error, str(e))

    def _show_error(self, msg):
        if hasattr(self, 'loading_lbl') and self.loading_lbl.winfo_exists():
            self.loading_lbl.destroy()
        if self.winfo_exists():
            ctk.CTkLabel(self.scroll, text=f"⚠️ Evaluation Error: {msg}", text_color="red", font=("Arial", 16)).pack(pady=20)

    def _render_dashboard(self):
        if hasattr(self, 'loading_lbl') and self.loading_lbl.winfo_exists():
            self.loading_lbl.destroy()
            
        if not self.winfo_exists(): return
        
        # 1. KPI Row
        kpi_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        kpi_frame.pack(fill="x", pady=(0, 20))
        
        metrics = [
            ("Model Accuracy", f"{self.metrics_data['accuracy']*100:.1f}%", "#00E5FF"),
            ("Precision", f"{self.metrics_data['precision']*100:.1f}%", "#2ed573"),
            ("Recall", f"{self.metrics_data['recall']*100:.1f}%", "#ffa502"),
            ("F1 Score", f"{self.metrics_data['f1']*100:.1f}%", "#ff4757")
        ]
        
        for i, (title, val, color) in enumerate(metrics):
            kpi_frame.grid_columnconfigure(i, weight=1)
            card = ctk.CTkFrame(kpi_frame, fg_color="#1e1e1e", corner_radius=10)
            card.grid(row=0, column=i, padx=10, sticky="ew")
            ctk.CTkLabel(card, text=title, font=("Arial", 14), text_color="#aaaaaa").pack(pady=(15, 0))
            ctk.CTkLabel(card, text=val, font=("Arial", 32, "bold"), text_color=color).pack(pady=(5, 15))

        # 2. Charts Row
        charts_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        charts_frame.pack(fill="both", expand=True, pady=10)
        charts_frame.grid_columnconfigure(0, weight=1)
        charts_frame.grid_columnconfigure(1, weight=1)

        # Matplotlib Dark Theme
        plt.style.use('dark_background')
        
        # -- Confusion Matrix --
        cm_card = ctk.CTkFrame(charts_frame, fg_color="#1e1e1e", corner_radius=10)
        cm_card.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(cm_card, text="Confusion Matrix", font=("Arial", 18, "bold")).pack(pady=(10,0))
        
        fig_cm, ax_cm = plt.subplots(figsize=(5, 4), facecolor='#1e1e1e')
        cax = ax_cm.matshow(self.metrics_data["confusion_matrix"], cmap='Blues')
        fig_cm.colorbar(cax)
        
        labels = ["High", "Medium", "Low"]
        ax_cm.set_xticks([0, 1, 2])
        ax_cm.set_yticks([0, 1, 2])
        ax_cm.set_xticklabels(labels)
        ax_cm.set_yticklabels(labels)
        ax_cm.set_xlabel('Predicted')
        ax_cm.set_ylabel('True')
        
        cm = self.metrics_data["confusion_matrix"]
        for i in range(3):
            for j in range(3):
                ax_cm.text(j, i, str(cm[i, j]), va='center', ha='center', color='black' if cm[i, j] > cm.max()/2 else 'white')
        
        canvas_cm = FigureCanvasTkAgg(fig_cm, master=cm_card)
        canvas_cm.draw()
        canvas_cm.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        # -- ROC Curve --
        roc_card = ctk.CTkFrame(charts_frame, fg_color="#1e1e1e", corner_radius=10)
        roc_card.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(roc_card, text="ROC Curve (Multi-Class)", font=("Arial", 18, "bold")).pack(pady=(10,0))
        
        fig_roc, ax_roc = plt.subplots(figsize=(5, 4), facecolor='#1e1e1e')
        y_true = self.metrics_data["y_true"]
        y_probs = self.metrics_data["y_probs"]
        
        if hasattr(self.model, 'classes_'):
            classes = self.model.classes_
            y_bin = label_binarize(y_true, classes=classes)
            colors = ['#ff4757', '#ffa502', '#2ed573']
            for i, cls in enumerate(classes):
                fpr, tpr, _ = roc_curve(y_bin[:, i], y_probs[:, i])
                roc_auc = auc(fpr, tpr)
                ax_roc.plot(fpr, tpr, color=colors[i%len(colors)], lw=2, label=f'{cls} (AUC={roc_auc:.2f})')
                
        ax_roc.plot([0, 1], [0, 1], '--', lw=2, color="#7f8fa6")
        ax_roc.set_xlim([0.0, 1.0])
        ax_roc.set_ylim([0.0, 1.05])
        ax_roc.set_xlabel('False Positive Rate')
        ax_roc.set_ylabel('True Positive Rate')
        ax_roc.legend(loc="lower right")
        
        canvas_roc = FigureCanvasTkAgg(fig_roc, master=roc_card)
        canvas_roc.draw()
        canvas_roc.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        # 3. Feature Importance Bar Chart
        if len(self.metrics_data["importances"]) > 0:
            feat_card = ctk.CTkFrame(self.scroll, fg_color="#1e1e1e", corner_radius=10)
            feat_card.pack(fill="x", padx=10, pady=(10, 20))
            ctk.CTkLabel(feat_card, text="Global Feature Importance", font=("Arial", 18, "bold")).pack(pady=(10,0))
            
            fig_feat, ax_feat = plt.subplots(figsize=(10, 3), facecolor='#1e1e1e')
            y_pos = np.arange(len(self.model_features))
            ax_feat.barh(y_pos, self.metrics_data["importances"], color="#00E5FF")
            ax_feat.set_yticks(y_pos)
            ax_feat.set_yticklabels(self.model_features)
            ax_feat.invert_yaxis()  # labels read top-to-bottom
            ax_feat.set_xlabel('Relative Importance')
            
            canvas_feat = FigureCanvasTkAgg(fig_feat, master=feat_card)
            canvas_feat.draw()
            canvas_feat.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
