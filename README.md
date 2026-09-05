<div align="center">

# 🎓 AcaDesk

### Student Risk Prediction & Academic Analytics System

**An ML-powered desktop application for identifying academically at-risk students and supporting early intervention.**

<br>

![Python](https://img.shields.io/badge/Python-3.x-blue?style=flat-square\&logo=python)
![Scikit-learn](https://img.shields.io/badge/ML-Scikit--learn-orange?style=flat-square)
![MySQL](https://img.shields.io/badge/Database-MySQL-4479A1?style=flat-square\&logo=mysql)
![CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-2E8B57?style=flat-square)

</div>

---

## 📌 Overview

**AcaDesk** is a desktop-based academic analytics and prediction system designed to help educational institutions identify students who may be at academic risk.

The system combines **student academic data, attendance, assignment performance, and backlog information** with machine-learning models to classify students into different risk levels.

Beyond prediction, AcaDesk provides institutional analytics and an intervention workflow so faculty and academic administrators can identify students requiring attention and track follow-up actions.

---

## 🎯 Problem

Educational institutions often have large amounts of student data but lack an effective way to turn that data into **early warnings**.

Students who are struggling academically may only be identified after their performance has already declined significantly.

AcaDesk approaches this as a predictive analytics problem:

> **Can existing academic data be used to identify students who are likely to struggle early enough for meaningful intervention?**

---

## 💡 Solution

AcaDesk connects academic data to a centralized desktop application that provides:

* Student risk prediction
* Risk-level classification
* Institutional performance analytics
* Department-level comparisons
* Automated identification of high-priority students
* Faculty intervention tracking
* Database and ERP integration

---

## ✨ Key Features

### 🔌 ERP & Database Integration

* Connects with existing **MySQL / MariaDB** academic databases.
* Provides an ERP setup workflow.
* Automatically detects relevant database schemas.
* Maps student, academic, and department information to the application's internal data model.

### 🧠 Machine Learning Risk Prediction

The prediction system uses academic indicators such as:

* Previous academic marks
* Attendance
* Assignment performance
* Backlog counts

Students are classified into:

* 🔴 **High Risk**
* 🟡 **Moderate Risk**
* 🟢 **Safe**

The system also provides prediction confidence information.

### 📊 Institutional Analytics

Provides analytical views across the institution, including:

* Overall pass-rate analysis
* Attendance trends
* Department comparisons
* Student-level analysis
* Interactive charts and visualizations

### 🚨 Early Warning System

The application can scan student data and identify students requiring attention.

This allows academic staff to focus their intervention efforts on students with higher predicted risk.

### 🤝 Intervention Tracking

Faculty and academic administrators can record and manage:

* Counseling sessions
* Action plans
* Follow-up activities
* Intervention history

### 🎨 Desktop Interface

AcaDesk includes a custom dark-mode desktop interface built with **CustomTkinter**, with interactive layouts and integrated visualizations.

---

## 🧠 Machine Learning

The project uses **Scikit-learn** along with Pandas and NumPy for its predictive analytics pipeline.

The repository currently includes prediction workflows based around **Random Forest and related predictive models**, including first-year and expanded-model training paths.

The general pipeline is:

```text
Student Academic Data
        │
        ▼
Data Collection
        │
        ▼
Feature Processing
        │
        ▼
Machine Learning Model
        │
        ▼
Risk Prediction
        │
        ▼
Risk Classification
        │
        ▼
Early Intervention
```

---

## 🏗️ Architecture

```text
┌─────────────────────────────┐
│      Academic / ERP Data    │
│       MySQL / MariaDB       │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│      Data & Schema Layer    │
│  Database + Schema Mapping  │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│       ML Prediction Layer   │
│   Scikit-learn / Pandas     │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│       Analytics Engine      │
│     Risk + Performance      │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│       Desktop UI Layer      │
│      CustomTkinter          │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│    Faculty Intervention     │
│       & Follow-up           │
└─────────────────────────────┘
```

---

## 🛠️ Technology Stack

| Area                 | Technologies           |
| -------------------- | ---------------------- |
| **Language**         | Python                 |
| **Machine Learning** | Scikit-learn           |
| **Data Processing**  | Pandas, NumPy          |
| **Desktop UI**       | CustomTkinter, Tkinter |
| **Visualization**    | Matplotlib             |
| **Database**         | MySQL, MariaDB         |
| **Local Storage**    | SQLite                 |
| **Application**      | Desktop / Windows      |

---

## 📂 Project Structure

```text
AcaDesk/
│
├── logic/              # Backend logic, database handlers and ML functionality
├── database/           # Database-related components
├── ui/                 # User interface components
├── scripts/             # Data generation and model training utilities
│
├── main.py              # Application entry point
├── dev_run.py           # Development runner
├── clean_dashboard.py   # Dashboard utility
├── build_app.bat        # Application build script
├── AcaDesk.spec         # PyInstaller configuration
│
├── README.md
└── .gitignore
```

---

## ⚙️ Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/i-am-abhinash/AcaDesk-Student-Risk-Prediction-System.git

cd AcaDesk-Student-Risk-Prediction-System
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure the database

AcaDesk can work with a MySQL / MariaDB-based academic database.

For local testing, configure the database connection according to the project's configuration.

> **Security note:** Never commit real database passwords, API keys, or other credentials to the repository.

### 4. Prepare test data

If using the project's test-data workflow:

```bash
python populate_erp.py
```

### 5. Train the models

To regenerate the prediction models:

```bash
python scripts/train_first_year_model.py
python scripts/train_expanded_model.py
```

### 6. Run the application

```bash
python main.py
```

---

## 🔐 Security

If connecting AcaDesk to a real institutional database:

* Do not commit database credentials.
* Use environment variables or a local configuration file.
* Keep production credentials outside version control.
* Use test/synthetic data when sharing the project publicly.

---

## 🔮 Future Improvements

Potential directions for further development include:

* Model performance benchmarking and validation
* Explainable AI for individual predictions
* More configurable prediction models
* Web-based administration
* Role-based access control
* Automated reporting
* Notification systems for high-risk students
* Deployment and monitoring infrastructure

---

## 👨‍💻 Author

### Gowri Abhinash

AI/ML Engineering Student & Software Developer

* GitHub: [@i-am-abhinash](https://github.com/i-am-abhinash)
* LinkedIn: [Gowri Abhinash](https://www.linkedin.com/in/gowri-abhinash-modugumudi-a7a1aa2b)

---

<div align="center">

**Built to turn academic data into actionable early-warning insights.**

⭐ If you find the project interesting, consider exploring the repository.

</div>
