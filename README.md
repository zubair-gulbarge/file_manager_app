"""# ☁️ CloudBox: Professional Multi-User File Manager

CloudBox is a production-ready, secure, and analytical web application built with Python and Flask. It allows multiple users to upload, manage, search, and categorize files in a private cloud environment, while providing administrators with high-level system analytics and user management tools.

## 🚀 Features

### **For Users**
* **Secure Authentication:** Login/Logout system with rate-limiting protection.
* **Real-time Uploads:** AJAX-powered file uploads with a live progress bar.
* **File Management:** View (inline), Download, and Delete files.
* **Organization:** Categorize files (Work, Personal, Invoices, etc.) and search by filename.
* **Storage Tracking:** Personal storage usage bar showing space occupied vs. the 16MB limit.

### **For Administrators**
* **System Analytics:** Visual breakdown of storage usage per user and file category distribution.
* **User Management:** Create new users, delete existing accounts, and toggle permissions (User vs. Admin).
* **File Oversight:** Ability to view and manage all files uploaded to the system.

## 🛠️ Technology Stack

* **Backend:** Python 3.x, Flask (Web Framework)
* **Database:** SQLite with SQLAlchemy ORM
* **Authentication:** Flask-Login
* **Security:** Flask-Limiter (Rate limiting), Werkzeug (Password Hashing)
* **Frontend:** HTML5, Tailwind CSS (Styling), JavaScript (AJAX/Progress Logic)
* **Fonts:** Inter (Google Fonts)

## 🧠 Core Concepts Implemented

* **CRUD Operations:** Full Create, Read, Update, and Delete functionality for both Files and Users.
* **Data Aggregation:** Using SQL `func.sum` and `group_by` to calculate storage statistics in real-time.
* **RESTful Routing:** Organized URL structures for downloading, viewing, and managing resources.
* **MIME Management:** Controlling HTTP headers (`Content-Disposition`) to switch between file viewing and forced downloading.
* **Frontend-Backend Sync:** Using AJAX (`XMLHttpRequest`) to communicate with the server without page refreshes.

## 📥 Installation & Setup

### **1. Clone or Copy the Project**
Ensure you have the following directory structure:
```text
file_manager_app/
├── app.py
├── models.py
├── templates/
│   ├── login.html
│   ├── dashboard.html
│   └── create_user.html
└── uploads/          # Directory where files are stored