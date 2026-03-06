# Face Recognition Attendance System

A modern, FastAPI-based attendance management system with face recognition capabilities, designed for educational institutions.

## Features

- 🎯 **Face Recognition**: Automatic attendance marking via facial recognition
- 👥 **Role-Based Access**: Admin, Faculty, Student, and Mentor roles with granular permissions
- 📊 **Attendance Tracking**: Subject-wise attendance with dual verification (face + faculty)
- ⚖️ **Dispute Resolution**: Admin/Mentor workflow for resolving attendance discrepancies
- 📈 **Reports & Analytics**: PDF/Excel export, threshold tracking, detailed analytics
- 🔔 **Notifications**: Automated alerts for low attendance and important updates
- 🗓️ **Schedule Management**: Class scheduling and academic session tracking
- 🔐 **Secure Authentication**: JWT-based authentication with bcrypt password hashing

## Architecture Overview

### Tech Stack

- **Framework**: FastAPI 0.104.1 (Python 3.12+)
- **Database**: SQLite with SQLAlchemy 2.0 (async ORM)
- **Authentication**: JWT tokens (HS256), bcrypt password hashing
- **Face Recognition**: OpenCV + face_recognition library
- **Testing**: pytest with async support
- **Background Tasks**: Celery + Redis (optional)
- **Exports**: ReportLab (PDF), openpyxl (Excel)

### Project Structure

```
app/
├── api/
│   ├── routes/          # API endpoints by domain
│   └── ws/              # WebSocket handlers
├── crud/                # Database operations layer
├── db/                  # Database configuration
├── middleware/          # Rate limiting, CORS, etc.
├── models/              # SQLAlchemy ORM models
├── schemas/             # Pydantic validation schemas
├── services/            # Business logic layer
├── static/              # CSS, JS assets
├── templates/           # Jinja2 HTML templates
├── utils/               # Helper functions (security, etc.)
└── workers/             # Background task definitions

tests/                   # Pytest test suite
migrations/              # Alembic database migrations
```

### Architecture Pattern

**Layer Separation**:
```
Route Layer → Service Layer → CRUD Layer → Database
   ↓              ↓              ↓
Schemas      Business Logic   SQLAlchemy
```

**Key Models**:
- `User`: Admin, Faculty, Student, Mentor with cohort assignment
- `SubjectAttendance`: Dual verification system (face + faculty)
- `FinalStatus`: PRESENT, DISPUTED, ABSENT, PENDING
- `Subject`: Course management with threshold tracking

## Development Setup

### Prerequisites

- Python 3.12 or higher
- Virtual environment tool (venv/virtualenv)
- Git

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd face_attendance_fastapi
   ```

2. **Create and activate virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   .\venv\Scripts\activate   # Windows
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Initialize database**:
   ```bash
   # Run migrations (if using Alembic)
   alembic upgrade head
   
   # Or let FastAPI create tables on first run
   ```

### Running the Application

#### Development Server

```bash
# From project root
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Access the application:
- **API**: http://localhost:8000
- **Documentation**: http://localhost:8000/docs (Swagger UI)
- **Alternative Docs**: http://localhost:8000/redoc

#### Production Server

```bash
# Using Gunicorn with Uvicorn workers
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

#### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or using Docker directly
docker build -t attendance-api .
docker run -p 8000:8000 attendance-api
```

### Running Tests

```bash
# Run all tests
unset PYTHONPATH && PYTHONNOUSERSITE=1 python -m pytest

# Run with coverage
unset PYTHONPATH && PYTHONNOUSERSITE=1 python -m pytest --cov=app

# Run specific test file
unset PYTHONPATH && PYTHONNOUSERSITE=1 python -m pytest tests/test_auth.py

# Run with verbose output
unset PYTHONPATH && PYTHONNOUSERSITE=1 python -m pytest -v

# Note: PYTHONNOUSERSITE=1 prevents ROS pytest plugin conflicts on systems with ROS installed
```

**Test Coverage**: 17/25 tests passing (core functionality validated)
- ✅ Authentication flow
- ✅ Protected endpoints
- ✅ Subject listing
- ✅ Dispute resolution (admin/mentor workflows)
- ⚠️ Some endpoint tests need API route adjustments

## API Quick Reference

### Authentication

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/auth/login` | Login with email/password | Public |
| GET | `/api/auth/me` | Get current user info | Required |
| GET | `/health` | Health check | Public |

### Subjects

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/subjects/` | List all subjects | Required |
| GET | `/api/subjects/{id}` | Get subject details | Required |
| POST | `/api/subjects/mark-attendance` | Mark attendance (Faculty) | Faculty+ |

### Attendance Management

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/subjects/attendance/{id}/resolve` | Resolve disputed record | Admin/Mentor |
| POST | `/api/admin/attendance/{id}/resolve` | Resolve disputed record (admin endpoint) | Admin/Mentor |
| GET | `/api/attendance/student/{id}` | Get student's attendance | Student+ |

### Exports

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/export/attendance/pdf` | Export attendance as PDF | Faculty+ |
| POST | `/api/export/attendance/excel` | Export attendance as Excel | Faculty+ |

### Admin

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/users/` | Create new user | Admin |
| GET | `/api/users/` | List all users | Admin |
| PUT | `/api/users/{id}` | Update user | Admin |

**Authentication**: Include JWT token in Authorization header:
```bash
Authorization: Bearer <your_jwt_token>
```

**Rate Limits**:
- Login: 5 requests per 60 seconds
- Face scan: 10 requests per 60 seconds

## Key Features Detail

### Dispute Resolution System

When face verification and faculty marking disagree, the system creates a `DISPUTED` status. 

**Resolution Workflow**:
1. Admin or Mentor navigates to disputed records
2. Reviews evidence (timestamp, location, subject context)
3. Sets final status (PRESENT/ABSENT) with notes
4. Record is locked to prevent further changes
5. Audit log tracks who resolved and when

**Access Control**:
- **Admin**: Can resolve any disputed record
- **Mentor**: Can only resolve for students in their assigned cohort (program/major/section)
- **Faculty**: Cannot resolve disputes (read-only)
- **Student**: Cannot resolve disputes

### Cohort System

Students and Mentors are assigned to cohorts for targeted management:
- **Program**: B.Tech, BCA, M.Tech, etc.
- **Major**: Computer Science, Electronics, etc.
- **Specialization**: AI/ML, Data Science, etc.
- **Section**: A, B, C, etc.

Mentors can only manage students within their assigned cohort.

### Dual Verification

Attendance is verified through two channels:
1. **Face Recognition**: Student scans face at class entry
2. **Faculty Marking**: Faculty marks roll call

**Final Status Logic**:
- Both verified → `PRESENT`
- Only one verified → `DISPUTED`
- Neither verified → `ABSENT`
- Awaiting verification → `PENDING`

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Database
DATABASE_URL=sqlite+aiosqlite:///./attendance.db

# JWT
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_HOURS=3

# Face Recognition
FACE_CONFIDENCE_THRESHOLD=60.0
KNN_K=5

# Attendance
ATTENDANCE_LOCK_DAYS=3

# GPS (set to 0.0 to disable)
CAMPUS_LAT=0.0
CAMPUS_LNG=0.0
CAMPUS_RADIUS_KM=0.5

# Optional: Email
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=

# Optional: Redis/Celery
REDIS_URL=
CELERY_BROKER_URL=
```

## Common Development Tasks

### Create a new user (Admin)

```bash
# Via API
curl -X POST "http://localhost:8000/api/users/" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": "FAC001",
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@university.edu",
    "password": "securepassword",
    "role": "Faculty",
    "department": "Computer Science"
  }'
```

### Run database migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1
```

### Clear rate limit cache (for testing)

```python
# In Python REPL
from app.middleware.rate_limit import _request_log
_request_log.clear()
```

## Troubleshooting

### bcrypt version warning

**Issue**: `(trapped) error reading bcrypt version` warning during authentication

**Solution**: Warning is non-fatal, login still works. To fix:
```bash
pip install --upgrade passlib bcrypt
```

### ROS pytest plugin conflicts

**Issue**: `PluginValidationError: unknown hook 'pytest_launch_collect_makemodule'`

**Solution**: Run tests with isolated environment:
```bash
unset PYTHONPATH && PYTHONNOUSERSITE=1 python -m pytest
```

### Database locked errors

**Issue**: `database is locked` errors in SQLite

**Solutions**:
- Use PostgreSQL for production (SQLite is single-writer)
- Increase connection timeout in DATABASE_URL
- Check for long-running transactions

## Contributing

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make changes and add tests
3. Ensure tests pass: `pytest`
4. Commit with clear messages (see commit history for examples)
5. Push and create a Pull Request

**Commit Message Format**:
```
<type>: <subject>

<body>
```

Types: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`

## License

[Add your license here]

## Support

For issues and questions:
- Create an issue in the repository
- Contact: developer@attendance.local

---

**Last Updated**: March 2026  
**Version**: 1.0.0
