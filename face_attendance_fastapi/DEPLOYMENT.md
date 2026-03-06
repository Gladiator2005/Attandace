# Deployment Guide

Complete guide for deploying the Face Recognition Attendance System to production.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Configuration](#environment-configuration)
- [Docker Deployment](#docker-deployment)
- [Cloud Platform Deployment](#cloud-platform-deployment)
  - [AWS Deployment](#aws-deployment)
  - [Google Cloud Platform](#google-cloud-platform)
  - [DigitalOcean](#digitalocean)
  - [Azure](#azure)
- [Database Setup](#database-setup)
- [SSL/HTTPS Configuration](#ssl-https-configuration)
- [CI/CD Deployment](#cicd-deployment)
- [Monitoring & Logging](#monitoring--logging)
- [Security Checklist](#security-checklist)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before deploying, ensure you have:

- [ ] Domain name (optional but recommended)
- [ ] SSL certificate or Let's Encrypt setup
- [ ] PostgreSQL database (recommended for production)
- [ ] Redis server (for background tasks)
- [ ] SMTP server credentials (for email notifications)
- [ ] Cloud provider account (AWS/GCP/Azure/DigitalOcean)
- [ ] Docker installed (for containerized deployment)

---

## Environment Configuration

### 1. Create Production Environment File

Create `.env.production` in the project root:

```bash
# Application Settings
APP_NAME="Face Attendance System"
ENVIRONMENT=production
DEBUG=False
API_V1_STR=/api

# Security
SECRET_KEY=your-super-secret-key-change-this-to-random-64-character-string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database
DATABASE_URL=postgresql+asyncpg://user:password@db-host:5432/attendance_db
# For SQLite (not recommended for production):
# DATABASE_URL=sqlite+aiosqlite:///./attendance.db

# Redis (for background tasks)
REDIS_URL=redis://redis-host:6379/0

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@yourdomain.com

# CORS Settings
CORS_ORIGINS=["https://yourdomain.com", "https://www.yourdomain.com"]

# Rate Limiting
RATE_LIMIT_ENABLED=True
MAX_REQUESTS_PER_MINUTE=60

# File Upload
MAX_UPLOAD_SIZE_MB=10
UPLOAD_DIR=/app/uploads

# Face Recognition
FACE_RECOGNITION_TOLERANCE=0.6
FACE_DETECTION_MODEL=hog

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/attendance/app.log
```

### 2. Generate Secure Secret Key

```bash
# Generate a secure random secret key
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 3. Configure Database

For production, use PostgreSQL instead of SQLite:

```bash
# Install PostgreSQL (Ubuntu/Debian)
sudo apt update
sudo apt install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
CREATE DATABASE attendance_db;
CREATE USER attendance_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE attendance_db TO attendance_user;
\q
```

---

## Docker Deployment

### Local Docker Deployment

1. **Build the Docker image**:

```bash
docker build -t face-attendance-api:latest .
```

2. **Run with Docker Compose**:

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: attendance_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: attendance_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U attendance_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  api:
    build: .
    image: face-attendance-api:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://attendance_user:${DB_PASSWORD}@db:5432/attendance_db
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
      - ENVIRONMENT=production
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/var/log/attendance
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    command: >
      sh -c "
        alembic upgrade head &&
        gunicorn app.main:app 
        --workers 4 
        --worker-class uvicorn.workers.UvicornWorker 
        --bind 0.0.0.0:8000 
        --timeout 120 
        --access-logfile - 
        --error-logfile -
      "

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
      - ./uploads:/usr/share/nginx/html/uploads:ro
    depends_on:
      - api
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

3. **Create `.env` file**:

```bash
DB_PASSWORD=your_secure_db_password
SECRET_KEY=your_secret_key_from_step_2
```

4. **Start services**:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

5. **Apply database migrations**:

```bash
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head
```

6. **Seed initial data** (optional):

```bash
docker-compose -f docker-compose.prod.yml exec api python scripts/db_manager.py seed
```

### Nginx Configuration

Create `nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream api {
        server api:8000;
    }

    server {
        listen 80;
        server_name yourdomain.com www.yourdomain.com;
        
        # Redirect HTTP to HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name yourdomain.com www.yourdomain.com;

        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;

        client_max_body_size 50M;

        location / {
            proxy_pass http://api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # WebSocket support
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            
            proxy_read_timeout 300s;
            proxy_connect_timeout 75s;
        }

        location /static {
            alias /usr/share/nginx/html/static;
            expires 30d;
            add_header Cache-Control "public, immutable";
        }

        location /uploads {
            alias /usr/share/nginx/html/uploads;
            expires 7d;
            add_header Cache-Control "public";
        }
    }
}
```

---

## Cloud Platform Deployment

### AWS Deployment

#### Option 1: AWS ECS (Elastic Container Service)

1. **Push Docker image to ECR**:

```bash
# Authenticate Docker to AWS ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Create repository
aws ecr create-repository --repository-name face-attendance-api

# Tag and push image
docker tag face-attendance-api:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/face-attendance-api:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/face-attendance-api:latest
```

2. **Create RDS PostgreSQL instance**:

```bash
aws rds create-db-instance \
  --db-instance-identifier attendance-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username admin \
  --master-user-password YourSecurePassword \
  --allocated-storage 20
```

3. **Create ECS Task Definition** (`task-definition.json`):

```json
{
  "family": "face-attendance-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "api",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/face-attendance-api:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "ENVIRONMENT",
          "value": "production"
        }
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:account-id:secret:attendance/db-url"
        },
        {
          "name": "SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:account-id:secret:attendance/secret-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/face-attendance-api",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "api"
        }
      }
    }
  ]
}
```

4. **Deploy to ECS**:

```bash
# Create ECS cluster
aws ecs create-cluster --cluster-name attendance-cluster

# Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

# Create service
aws ecs create-service \
  --cluster attendance-cluster \
  --service-name attendance-api \
  --task-definition face-attendance-api \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

#### Option 2: AWS Elastic Beanstalk

1. **Install EB CLI**:

```bash
pip install awsebcli
```

2. **Initialize Elastic Beanstalk**:

```bash
eb init -p docker face-attendance-api --region us-east-1
```

3. **Create environment**:

```bash
eb create production-env \
  --database.engine postgres \
  --database.instance db.t3.micro
```

4. **Deploy**:

```bash
eb deploy
```

5. **Configure environment variables**:

```bash
eb setenv SECRET_KEY=your-secret-key \
  SMTP_HOST=smtp.gmail.com \
  SMTP_USER=your-email@gmail.com
```

---

### Google Cloud Platform

1. **Build and push to Google Container Registry**:

```bash
# Configure gcloud
gcloud config set project your-project-id

# Build and push
gcloud builds submit --tag gcr.io/your-project-id/face-attendance-api

# Or use Cloud Build
gcloud builds submit --config cloudbuild.yaml
```

2. **Create Cloud SQL PostgreSQL instance**:

```bash
gcloud sql instances create attendance-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1
```

3. **Deploy to Cloud Run**:

```bash
gcloud run deploy face-attendance-api \
  --image gcr.io/your-project-id/face-attendance-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars ENVIRONMENT=production \
  --set-secrets DATABASE_URL=attendance-db-url:latest,SECRET_KEY=attendance-secret:latest \
  --add-cloudsql-instances your-project-id:us-central1:attendance-db
```

4. **Map custom domain**:

```bash
gcloud run domain-mappings create \
  --service face-attendance-api \
  --domain api.yourdomain.com \
  --region us-central1
```

---

### DigitalOcean

1. **Create Droplet with Docker**:

```bash
# Use their Docker 1-Click App or create Ubuntu droplet
doctl compute droplet create attendance-api \
  --image docker-20-04 \
  --size s-2vcpu-4gb \
  --region nyc1 \
  --ssh-keys your-ssh-key-id
```

2. **SSH into droplet**:

```bash
ssh root@your-droplet-ip
```

3. **Clone repository and setup**:

```bash
git clone https://github.com/your-username/attendance-system.git
cd attendance-system/face_attendance_fastapi

# Create .env file
nano .env.production

# Start with Docker Compose
docker-compose -f docker-compose.prod.yml up -d
```

4. **Setup firewall**:

```bash
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

#### Using DigitalOcean App Platform

1. **Create `app.yaml`**:

```yaml
name: face-attendance-api
region: nyc
services:
  - name: api
    github:
      repo: your-username/attendance-system
      branch: main
      deploy_on_push: true
    dockerfile_path: face_attendance_fastapi/Dockerfile
    instance_count: 2
    instance_size_slug: basic-xs
    http_port: 8000
    routes:
      - path: /
    envs:
      - key: ENVIRONMENT
        value: production
      - key: DATABASE_URL
        value: ${db.DATABASE_URL}
      - key: SECRET_KEY
        scope: RUN_TIME
        type: SECRET
    health_check:
      http_path: /api/health

databases:
  - name: db
    engine: PG
    version: "15"
    production: true
    cluster_name: attendance-db
```

2. **Deploy**:

```bash
doctl apps create --spec app.yaml
```

---

### Azure

1. **Create Container Registry**:

```bash
az acr create --resource-group attendance-rg \
  --name attendanceregistry \
  --sku Basic

# Login
az acr login --name attendanceregistry
```

2. **Push image**:

```bash
docker tag face-attendance-api attendanceregistry.azurecr.io/face-attendance-api:latest
docker push attendanceregistry.azurecr.io/face-attendance-api:latest
```

3. **Create PostgreSQL**:

```bash
az postgres server create \
  --resource-group attendance-rg \
  --name attendance-db-server \
  --location eastus \
  --admin-user adminuser \
  --admin-password SecurePassword123! \
  --sku-name B_Gen5_1
```

4. **Deploy to App Service**:

```bash
az webapp create \
  --resource-group attendance-rg \
  --plan attendance-plan \
  --name face-attendance-api \
  --deployment-container-image-name attendanceregistry.azurecr.io/face-attendance-api:latest

# Configure environment
az webapp config appsettings set \
  --resource-group attendance-rg \
  --name face-attendance-api \
  --settings DATABASE_URL=postgresql://... SECRET_KEY=...
```

---

## Database Setup

### PostgreSQL Migration from SQLite

1. **Export data from SQLite** (if migrating):

```bash
# Install pgloader
sudo apt install pgloader

# Create migration script
pgloader sqlite://attendance.db postgresql://user:pass@host/db
```

2. **Run migrations on production database**:

```bash
# Set production database URL
export DATABASE_URL=postgresql+asyncpg://user:password@host:5432/attendance_db

# Run migrations
alembic upgrade head

# Verify
alembic current
```

3. **Configure connection pooling**:

Update `app/db/session.py`:

```python
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)
```

---

## SSL/HTTPS Configuration

### Option 1: Let's Encrypt with Certbot

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal (cron)
sudo certbot renew --dry-run
```

### Option 2: Cloudflare (Free SSL)

1. Add your domain to Cloudflare
2. Update nameservers
3. Enable "Full (strict)" SSL mode
4. Enable "Always Use HTTPS"

### Option 3: AWS Certificate Manager

```bash
# Request certificate
aws acm request-certificate \
  --domain-name yourdomain.com \
  --subject-alternative-names www.yourdomain.com \
  --validation-method DNS
```

---

## CI/CD Deployment

The GitHub Actions workflows are already configured. To enable automated deployment:

### 1. Configure GitHub Secrets

Go to your repository → Settings → Secrets and variables → Actions, add:

```
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_REGION
ECR_REPOSITORY

# Or for other platforms
DOCKER_USERNAME
DOCKER_PASSWORD
DIGITALOCEAN_ACCESS_TOKEN
```

### 2. Update Docker Workflow

Modify `.github/workflows/docker.yml` to add deployment step:

```yaml
- name: Deploy to Production
  if: github.ref == 'refs/heads/main'
  run: |
    # Example: Deploy to AWS ECS
    aws ecs update-service \
      --cluster attendance-cluster \
      --service attendance-api \
      --force-new-deployment
```

### 3. Deployment Strategy

The workflow automatically:
- ✅ Runs tests on push
- ✅ Builds Docker image on main branch
- ✅ Scans for vulnerabilities with Trivy
- ✅ Pushes to container registry
- 🔄 **You add**: Deploy to your platform

---

## Monitoring & Logging

### Application Logging

Configure structured logging in `app/main.py`:

```python
import logging
from pythonjsonlogger import jsonlogger

# Setup JSON logging
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)
```

### APM Solutions

#### 1. Sentry (Error Tracking)

```bash
pip install sentry-sdk[fastapi]
```

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn="your-sentry-dsn",
    integrations=[FastApiIntegration()],
    traces_sample_rate=1.0,
    environment="production"
)
```

#### 2. Datadog (Full Observability)

```bash
pip install ddtrace
```

```bash
ddtrace-run gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker
```

#### 3. Prometheus + Grafana

Add `prometheus-fastapi-instrumentator`:

```python
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()
Instrumentator().instrument(app).expose(app)
```

### Health Checks

Already configured at `/api/health`. Monitor with:

```bash
# Uptime monitoring services
- UptimeRobot
- Pingdom
- StatusCake

# Or custom script
*/5 * * * * curl -f https://yourdomain.com/api/health || alert
```

---

## Security Checklist

Before going live, verify:

- [ ] **Environment Variables**: No secrets in code, use `.env` or secrets manager
- [ ] **Secret Key**: Changed from default, 64+ characters random
- [ ] **Database**: Using PostgreSQL with strong password
- [ ] **HTTPS**: SSL certificate installed and enforced
- [ ] **CORS**: Configured with specific origins, not `*`
- [ ] **Rate Limiting**: Enabled and tuned
- [ ] **Input Validation**: Pydantic schemas validate all inputs
- [ ] **SQL Injection**: Using ORM (SQLAlchemy) - protected by default
- [ ] **XSS Protection**: Template escaping enabled
- [ ] **CSRF**: Tokens implemented for state-changing operations
- [ ] **Authentication**: JWT tokens with expiration
- [ ] **Password Hashing**: bcrypt with proper rounds
- [ ] **File Uploads**: Size limits, type validation, virus scanning
- [ ] **Dependency Scanning**: `safety check` in CI/CD
- [ ] **Container Scanning**: Trivy scans in CI/CD
- [ ] **Firewall**: Only ports 80, 443, (22 for SSH) open
- [ ] **Backups**: Database automated backups enabled
- [ ] **Monitoring**: Error tracking and alerts configured
- [ ] **Logs**: Centralized logging without sensitive data
- [ ] **Updates**: Plan for security patches

### Run Security Audit

```bash
# Check dependencies
safety check

# Scan Docker image
trivy image face-attendance-api:latest

# Scan code
bandit -r app/

# Check for common issues
pip install pip-audit
pip-audit
```

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Fails

```bash
# Check connectivity
pg_isadmin -h db-host -U user -d attendance_db

# Verify connection string
echo $DATABASE_URL

# Check firewall rules
telnet db-host 5432
```

#### 2. Migrations Fail

```bash
# Check current version
alembic current

# View migration history
alembic history

# Downgrade and retry
alembic downgrade -1
alembic upgrade head
```

#### 3. Performance Issues

```bash
# Check container resources
docker stats

# Monitor database queries
# Add to settings
echo_pool=True

# Increase workers
gunicorn --workers 8 --worker-class uvicorn.workers.UvicornWorker
```

#### 4. High Memory Usage

```bash
# Limit workers based on RAM
workers = (2 * CPU_COUNT) + 1

# Use worker timeout
--timeout 120

# Enable max-requests for worker recycling
--max-requests 1000 --max-requests-jitter 50
```

### Debug Mode

**Never enable in production**, but for controlled debugging:

```python
# Temporarily enable DEBUG for specific endpoint
import logging
logging.getLogger("sqlalchemy.engine").setLevel(logging.DEBUG)
```

---

## Post-Deployment

### 1. Verify Deployment

```bash
# Health check
curl https://yourdomain.com/api/health

# Test API
curl https://yourdomain.com/api/docs

# Check metrics
curl https://yourdomain.com/metrics
```

### 2. Create Admin User

```bash
# SSH into server or exec into container
docker exec -it attendance-api python scripts/db_manager.py seed

# Or via API
curl -X POST https://yourdomain.com/api/users/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@yourdomain.com", "password": "SecurePass123!", "role": "Admin"}'
```

### 3. Setup Backups

```bash
# PostgreSQL backup cron
0 2 * * * pg_dump -U user attendance_db | gzip > /backups/attendance_$(date +\%Y\%m\%d).sql.gz

# Retain 30 days
find /backups -name "attendance_*.sql.gz" -mtime +30 -delete
```

### 4. Monitor Logs

```bash
# Docker logs
docker logs -f attendance-api

# System logs
tail -f /var/log/attendance/app.log

# CloudWatch (AWS)
aws logs tail /ecs/face-attendance-api --follow
```

---

## Scaling Considerations

### Horizontal Scaling

1. **Load Balancer**: Use AWS ALB, GCP Load Balancer, or Nginx
2. **Multiple Instances**: Scale ECS tasks, Cloud Run instances, or Kubernetes pods
3. **Database Read Replicas**: For read-heavy workloads
4. **Caching**: Add Redis for session storage, rate limiting
5. **CDN**: CloudFlare, CloudFront for static assets

### Vertical Scaling

1. Increase container CPU/memory
2. Upgrade database instance type
3. Optimize queries with indexes

---

## Support

For deployment issues:

1. Check logs first: `docker logs` or cloud platform logs
2. Review [troubleshooting section](#troubleshooting)
3. Verify all environment variables are set
4. Test health endpoint
5. Check database connectivity

**Security Disclosure**: Report security issues to security@yourdomain.com

---

**🚀 Your application is now production-ready!**

Remember to:
- Monitor regularly
- Keep dependencies updated
- Review logs for anomalies
- Test backups periodically
- Plan for disaster recovery
