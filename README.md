# ManageX - Construction ERP System

A comprehensive Enterprise Resource Planning (ERP) system for construction companies, built with Django 6.0.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Django](https://img.shields.io/badge/Django-6.0-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 🚀 Features

- **Dashboard** - Overview of projects, employees, and key metrics with role-based views
- **Employee Management** - Track workers, supervisors, salaries, and roles
- **Project Management** - Manage construction sites, milestones, budgets, and progress tracking
- **Attendance Tracking** - Record and monitor employee attendance with filtering and export
- **Attendance Automation** - Automated absenteeism script runs daily at 1:00 PM IST
- **Fuel Tracking** - Monitor fuel consumption for vehicles and equipment
- **Vehicle Management** - Manage company vehicles and assignments
- **Role-Based Access Control** - Admin, Supervisor, and Worker roles with appropriate permissions

## 🛠️ Tech Stack

- **Backend**: Django 6.0
- **Database**: SQLite (development) / PostgreSQL (production recommended)
- **Frontend**: Bootstrap 5, Crispy Forms
- **Authentication**: Django's built-in auth system with custom user model

## 📦 Installation

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- Git

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/managex-erp.git
   cd managex-erp
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run database migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create a superuser (admin account)**
   ```bash
   python manage.py createsuperuser
   ```
   Follow the prompts to set your username, email, and password.

6. **Run the development server**
   ```bash
   python manage.py runserver
   ```

7. **Access the application**
   - Open your browser: `http://127.0.0.1:8000`
   - Login with your superuser credentials

## 📁 Project Structure

```
managex-erp/
├── attendance/          # Attendance tracking module
├── construction_erp/    # Main project settings & URLs
├── core/                # Core app (dashboard, shared templates, utilities)
├── fuel/                # Fuel tracking module
├── projects/            # Project & milestone management
├── users/               # User management & authentication
├── vehicles/            # Vehicle management module
├── manage.py            # Django CLI
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

## 🔐 Security Notes

### For Development
The project is configured for development with sensible defaults:
- `DEBUG=True` by default
- SQLite database for easy setup
- The `SECRET_KEY` has a fallback value (prefixed with `django-insecure-`) which is fine for local development

### For Production Deployment
Before deploying to production, you **MUST**:

1. **Set environment variables**:
   ```bash
   # Generate a new secret key
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   
   # Set the environment variables
   export DJANGO_SECRET_KEY='your-generated-secret-key'
   export DEBUG=False
   export ALLOWED_HOSTS='yourdomain.com,www.yourdomain.com'
   ```

2. **Use a production database** (PostgreSQL recommended)

3. **Configure static files hosting**

### Default Password Reset Feature
The admin panel includes a "Reset Password" feature that resets employee passwords to `worker123`. This is an **intentional feature** for convenience in managing worker accounts. In production, consider:
- Changing the default reset password
- Implementing email-based password reset instead

## 🌐 Environment Variables

| Variable | Description | Default | Required in Production |
|----------|-------------|---------|------------------------|
| `DJANGO_SECRET_KEY` | Cryptographic key for security | Development fallback | ✅ Yes |
| `DEBUG` | Enable debug mode | `True` | ✅ Must be `False` |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts | `*` | ✅ Yes |

## 👥 User Roles

| Role | Permissions |
|------|-------------|
| **Admin** | Full access - manage all modules, users, and settings |
| **Supervisor** | View/manage workers, record attendance, view projects |
| **Worker** | View own dashboard, attendance history |

## 🤖 Attendance Automation

The system includes a self-triggering automation for marking absentees:
- **Trigger**: Runs automatically daily when any page is accessed after **1:00 PM IST**.
- **Logic**: Marks all active workers/supervisors who haven't updated their status as `ABSENT`.
- **Lockout**: Once auto-marked, workers cannot check in; only Admins or Supervisors can manually override.
- **Logs**: Daily summaries are stored in `attendance_logs/` (kept for a rolling 7-day period).

## 📊 Screenshots

*Coming soon*

## 🚀 Deployment

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for detailed deployment instructions for:
- PythonAnywhere
- Heroku
- DigitalOcean
- AWS

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is for educational and portfolio purposes.

## 👤 Author

**Ritik**

---

## ⚠️ Security Checklist Before Deployment

- [ ] Generate and set a new `DJANGO_SECRET_KEY`
- [ ] Set `DEBUG=False`
- [ ] Configure `ALLOWED_HOSTS` properly
- [ ] Use PostgreSQL or MySQL instead of SQLite
- [ ] Enable HTTPS
- [ ] Set up proper logging
- [ ] Review and configure `CSRF_TRUSTED_ORIGINS`
