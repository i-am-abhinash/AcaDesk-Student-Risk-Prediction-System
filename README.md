# AcaDesk - Student Risk Prediction & Analytics System

## 🚀 Overview
AcaDesk is a comprehensive, Machine Learning-based desktop application designed to help educational institutions identify students at academic risk, analyze institutional performance, and manage early interventions. 

Featuring a sleek, custom-built "Midnight Glass" dark mode interface, AcaDesk connects seamlessly to an institution's existing ERP/database, automatically detects schemas, and runs predictive analytics using Scikit-learn to flag students who might struggle with upcoming semesters.

---

## ✨ Key Features

### 🔌 Auto-Detect ERP Setup Wizard
- **Zero-Config Database Integration:** Institutions can connect AcaDesk to their existing MySQL/MariaDB databases without writing any code.
- **Intelligent Schema Detection:** Automatically scans and detects student, academic, and department tables, mapping them to AcaDesk's internal engine using keyword confidence scoring.

### 🧠 AI-Powered Risk Prediction
- **First-Year & Advanced Models:** Uses robust Random Forest and predictive algorithms to analyze 10th/12th-grade marks, current attendance, assignment scores, and backlog counts.
- **Risk Stratification:** Classifies students into High Risk, Moderate Risk, and Safe categories, providing confidence scores for each prediction.

### 📊 Institutional Analytics Dashboard
- **Macro & Micro Views:** View college-wide pass rates, attendance trends, and department-by-department comparisons.
- **Interactive Visualizations:** Features interactive radar charts, bar graphs, and trend plots directly inside the application using Matplotlib and CustomTkinter integrations.

### 🛡️ Early Warning & Intervention System
- **Automated Flagging:** Automatically scans the entire student body to generate a list of high-priority students requiring immediate attention.
- **Intervention Tracking:** Allows HODs and faculty to log, track, and manage specific counseling sessions, action plans, and interventions for at-risk students.

### 🎨 Premium "Midnight Glass" UI
- Built from the ground up using `customtkinter`, featuring fluid animations, responsive layouts, hover effects, and a highly polished dark-mode aesthetic.

---

## 🛠️ Tech Stack
- **Frontend / GUI:** Python, CustomTkinter, Tkinter, Matplotlib (for integrated graphs)
- **Backend Logic:** Python
- **Database:** MySQL / MariaDB (ERP Data), SQLite (Centralized Authentication & Local Caching)
- **Machine Learning:** Scikit-learn, Pandas, NumPy
- **Environment:** Windows / Cross-platform

---

## 📂 Project Structure

```text
AcaDesk/
│── logic/               # Backend logic, DB handlers, ML predictors, and schema detection
│── ui/                  # CustomTkinter GUI screens, widgets, and styles
│── scripts/             # Data generation and ML model training scripts
│── main.py              # Application entry point and router
│── populate_erp.py      # Script to generate a dummy ERP database for testing
│── README.md            
│── requirements.txt     
```

---

## ⚙️ Setup & Installation

**1. Clone the repository:**
```bash
git clone https://github.com/i-am-abhinash/AcaDesk-Student-Risk-Prediction-System.git
cd AcaDesk-Student-Risk-Prediction-System
```

**2. Install dependencies:**
```bash
pip install -r requirements.txt
```

**3. Database Setup (For Local Testing):**
If you do not have an existing ERP database, you can generate a massive dummy dataset for testing:
```bash
python populate_erp.py
```

**4. Security Key Setup:**
AcaDesk uses Fernet symmetric encryption for sensitive data (like database credentials). You must create a master encryption key before running the app for the first time.
To generate and store the key in `~/.acadesk/secret.key`, you can run:
```bash
python -c "import os; from cryptography.fernet import Fernet; os.makedirs(os.path.expanduser('~/.acadesk'), exist_ok=True); open(os.path.expanduser('~/.acadesk/secret.key'), 'wb').write(Fernet.generate_key())"
```

**5. Architecture Overview (Central vs Local DBs):**
AcaDesk uses a hybrid architecture to ensure security and performance:
- **ERP Database (MySQL/MariaDB):** Treated as **Read-Only**. AcaDesk will never write to your institution's ERP.
- **Central Auth DB (`acadesk_central.db`):** An SQLite database used for centralized user authentication, faculty notes, and auditing.
- **Local Cache DB (`local_cache.db`):** An SQLite database used for fast, offline access to analysis results and encrypted ERP connection configurations.

**6. Train the ML Models (Optional):**
To regenerate or retrain the Random Forest prediction models based on the current database:
```bash
python scripts/train_first_year_model.py
python scripts/train_expanded_model.py
```

**7. Run the application:**
```bash
python main.py
```

---

## 👨‍💻 Author
**Gowri Abhinash**  
GitHub: [i-am-abhinash](https://github.com/i-am-abhinash)  
LinkedIn: [Gowri Abhinash](https://www.linkedin.com/in/gowri-abhinash-modugumudi-a7a1aa2b1)
