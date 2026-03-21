# Academiq - Student Faculty Management System

A Django-based student and faculty management portal with attendance tracking and course management.

## Setup Instructions

### 1. Prerequisites
- Python 3.10+
- Git

### 2. Installation
Clone the repository and install dependencies:
```bash
git clone <repository-url>
cd "Student Faculty management"
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the root directory and add your email credentials (based on `.env.example`):
```env
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

### 4. Running the Project
```bash
python manage.py runserver
```

### 5. Database
This project uses `db_v2.sqlite3` as the default database. Ensure it is present in the root directory.