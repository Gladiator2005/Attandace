# Free Deployment Guide

Complete guide for deploying the Face Attendance System on **free hosting platforms**.

---

## 🏆 Recommended: Render.com (Easiest)

**Why Render:**
- ✅ Completely free tier (no credit card required initially)
- ✅ Free PostgreSQL database included
- ✅ Auto-deploy from GitHub
- ✅ Free SSL certificates
- ✅ Easy to use dashboard
- ⚠️ Apps sleep after 15 min inactivity (first request takes ~30s to wake)

### Step-by-Step Deployment

#### 1. Prepare Your Repository

Create `render.yaml` in your project root:

```yaml
services:
  - type: web
    name: face-attendance-api
    env: python
    region: oregon
    plan: free
    branch: main
    buildCommand: |
      cd face_attendance_fastapi
      pip install -r requirements.txt
      pip install gunicorn
    startCommand: |
      cd face_attendance_fastapi
      alembic upgrade head
      gunicorn app.main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
    healthCheckPath: /api/health
    envVars:
      - key: ENVIRONMENT
        value: production
      - key: DEBUG
        value: False
      - key: SECRET_KEY
        generateValue: true
      - key: DATABASE_URL
        fromDatabase:
          name: attendance-db
          property: connectionString
      - key: PYTHON_VERSION
        value: 3.12.0

databases:
  - name: attendance-db
    plan: free
    databaseName: attendance
    user: attendance_user
```

#### 2. Push to GitHub

```bash
cd /home/dhruv-kumar/Desktop/PROJECT/Attandace
git add render.yaml
git commit -m "feat: add Render deployment config"
git push origin main
```

#### 3. Deploy on Render

1. Go to https://render.com and sign up (free, use GitHub)
2. Click **"New"** → **"Blueprint"**
3. Connect your GitHub repository
4. Select the repository with `render.yaml`
5. Click **"Apply"**
6. Wait 5-10 minutes for deployment

#### 4. Access Your App

```
https://face-attendance-api.onrender.com
```

### Render Environment Variables

After deployment, add these in Render Dashboard → Environment:

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
CORS_ORIGINS=https://face-attendance-api.onrender.com
```

**Important:** Each time you add/change env vars, Render redeploys automatically.

---

## 🚀 Alternative 1: Fly.io (Best for Docker)

**Why Fly.io:**
- ✅ Great free tier (3 VMs, 3GB storage)
- ✅ Docker-based (our app is ready!)
- ✅ Multiple regions
- ✅ Always-on (doesn't sleep)
- ⚠️ Requires credit card for verification (won't charge on free tier)

### Deployment Steps

#### 1. Install Fly CLI

```bash
# Linux
curl -L https://fly.io/install.sh | sh

# Add to PATH
echo 'export FLYCTL_INSTALL="/home/dhruv-kumar/.fly"' >> ~/.bashrc
echo 'export PATH="$FLYCTL_INSTALL/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

#### 2. Login and Initialize

```bash
cd /home/dhruv-kumar/Desktop/PROJECT/Attandace/face_attendance_fastapi

# Login (will open browser)
flyctl auth login

# Initialize app
flyctl launch
```

Answer the prompts:
- App name: `face-attendance-api` (or auto-generated)
- Region: Choose closest to you
- PostgreSQL: **Yes** (free tier)
- Redis: **No** (can add later if needed)

This creates `fly.toml`:

```toml
app = "face-attendance-api"
primary_region = "ord"

[build]
  dockerfile = "Dockerfile"

[env]
  ENVIRONMENT = "production"
  DEBUG = "False"
  PORT = "8000"

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = false
  auto_start_machines = true
  min_machines_running = 1

  [[http_service.checks]]
    grace_period = "10s"
    interval = "30s"
    method = "GET"
    timeout = "5s"
    path = "/api/health"

[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 256
```

#### 3. Set Secrets

```bash
# Generate and set secret key
flyctl secrets set SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(64))")

# Set other secrets
flyctl secrets set SMTP_HOST=smtp.gmail.com
flyctl secrets set SMTP_USER=your-email@gmail.com
flyctl secrets set SMTP_PASSWORD=your-app-password
```

#### 4. Update Dockerfile for Fly.io

The Dockerfile needs to run migrations on startup. Create `entrypoint.sh`:

```bash
#!/bin/bash
set -e

# Run migrations
alembic upgrade head

# Seed data if first deployment
python scripts/db_manager.py seed || true

# Start server
exec "$@"
```

Update `Dockerfile`:

```dockerfile
# Add after WORKDIR /app
COPY entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

# Replace CMD with:
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 5. Deploy

```bash
# Deploy to Fly.io
flyctl deploy

# Check status
flyctl status

# View logs
flyctl logs
```

#### 6. Access Your App

```
https://face-attendance-api.fly.dev
```

### Fly.io Database Connection

Get the database URL:

```bash
# List databases
flyctl postgres list

# Get connection string
flyctl postgres connect -a <postgres-app-name>
```

The `DATABASE_URL` is automatically set as a secret.

---

## 🌐 Alternative 2: Railway.app (Developer Friendly)

**Why Railway:**
- ✅ $5 free credit per month (enough for small projects)
- ✅ Very easy deployment from GitHub
- ✅ PostgreSQL included
- ✅ Beautiful dashboard
- ⚠️ Credit card required after trial
- ⚠️ Free credit may run out mid-month with high usage

### Deployment Steps

#### 1. Deploy on Railway

1. Go to https://railway.app
2. Sign up with GitHub
3. Click **"New Project"** → **"Deploy from GitHub repo"**
4. Select your repository
5. Railway auto-detects Dockerfile

#### 2. Add PostgreSQL

1. Click **"New"** → **"Database"** → **"PostgreSQL"**
2. Railway automatically sets `DATABASE_URL` variable

#### 3. Configure Environment Variables

In Railway dashboard, add:

```
SECRET_KEY=<generate-with-command-below>
ENVIRONMENT=production
DEBUG=False
SMTP_HOST=smtp.gmail.com
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

Generate secret key:
```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

#### 4. Run Migrations

In Railway dashboard → **Settings** → **Deploy**:

Set **Custom Start Command**:
```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

#### 5. Access Your App

Railway provides a URL like: `https://face-attendance-api-production.up.railway.app`

---

## 💎 Alternative 3: Oracle Cloud Always Free (Most Generous)

**Why Oracle Cloud:**
- ✅ **Always Free** tier (not a trial!)
- ✅ 2 VMs with 1GB RAM each (can run 24/7)
- ✅ 200GB storage
- ✅ 10TB outbound data/month
- ✅ Most generous free tier available
- ⚠️ More complex setup (requires cloud knowledge)
- ⚠️ Requires credit card verification

**Perfect for:** Long-term free hosting with no time limits

### Quick Setup

1. **Create Account**: https://cloud.oracle.com/free
2. **Create Compute Instance**:
   - Shape: VM.Standard.E2.1.Micro (Always Free)
   - OS: Ubuntu 22.04
   - Add SSH key

3. **SSH into Instance**:
```bash
ssh ubuntu@<instance-ip>
```

4. **Install Docker**:
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo apt install docker-compose -y
```

5. **Deploy Application**:
```bash
# Clone repository
git clone <your-repo-url>
cd attendance-system/face_attendance_fastapi

# Create .env.production (add your values)
nano .env.production

# Start with Docker Compose
docker-compose -f docker-compose.prod.yml up -d
```

6. **Configure Firewall**:
```bash
# Oracle Cloud security list (via web console)
# Add Ingress Rules: Port 80, 443

# Instance firewall
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

7. **Setup Domain** (optional):
   - Point your domain A record to instance IP
   - Install Let's Encrypt SSL

---

## 📊 Comparison Table

| Platform | Free Tier | Database | Sleep? | Setup Time | Best For |
|----------|-----------|----------|--------|------------|----------|
| **Render.com** | ✅ Forever | ✅ Free PG | ⚠️ Yes (15min) | 5 min | **Beginners** |
| **Fly.io** | ✅ 3 VMs | ✅ Free PG | ❌ No | 10 min | **Docker users** |
| **Railway** | ⚠️ $5/month | ✅ Free PG | ❌ No | 5 min | Quick testing |
| **Oracle Cloud** | ✅ Forever | ⚠️ Self-host | ❌ No | 30 min | **Long-term** |
| **PythonAnywhere** | ✅ Forever | ⚠️ MySQL only | ❌ No | 15 min | Python apps |
| **Heroku** | ❌ Min $5 | ❌ Paid only | - | - | ~~Not free~~ |

---

## 🎯 My Recommendation for You

Based on **free + intermediate + normal project**, here's your best path:

### **START HERE: Render.com** (5 minutes)

**Pros:**
- Zero configuration needed
- Free PostgreSQL included
- Auto-deploy from GitHub
- Free SSL

**Only Downside:** 
- App sleeps after 15min inactivity (first request slow)
- **Solution:** Use free uptime monitor to ping every 14min

### **If You Want Always-On: Fly.io** (10 minutes)

**Pros:**
- Doesn't sleep
- Docker-based (you already have Dockerfile)
- Better performance than Render

**Setup:**
```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Deploy in 3 commands
cd face_attendance_fastapi
flyctl launch
flyctl deploy
```

---

## 🚀 Quick Start: Deploy to Render NOW

Follow these **exact steps** to deploy in 5 minutes:

### 1. Create render.yaml

I'll create it for you:

```bash
cd /home/dhruv-kumar/Desktop/PROJECT/Attandace
# (render.yaml will be created)
```

### 2. Push to GitHub

```bash
git add render.yaml
git commit -m "feat: add Render deployment"
git push
```

### 3. Deploy on Render

1. Visit: https://dashboard.render.com/register
2. Sign up with GitHub
3. New → Blueprint
4. Connect your repo
5. Click "Apply"

**Done!** Your app will be live at `https://your-app.onrender.com` in ~5 minutes.

---

## 🔧 Post-Deployment: Keep Free App Awake

Since Render free tier sleeps after 15min inactivity:

### Option 1: Cron Job (Free)

Use **cron-job.org** (free service):

1. Sign up at https://cron-job.org
2. Create new cron job:
   - URL: `https://your-app.onrender.com/api/health`
   - Interval: Every 14 minutes
3. Save

### Option 2: UptimeRobot (Free)

1. Sign up at https://uptimerobot.com
2. Add new monitor:
   - Type: HTTP(s)
   - URL: `https://your-app.onrender.com/api/health`
   - Interval: 5 minutes
3. Save

**This keeps your app always warm!**

---

## 🔐 Free SSL/HTTPS

All recommended platforms provide **free SSL automatically**:

- ✅ Render.com - Automatic SSL
- ✅ Fly.io - Automatic SSL  
- ✅ Railway - Automatic SSL

No configuration needed!

---

## 📧 Free Email Service (for notifications)

Your app needs SMTP for email notifications. Free options:

### Option 1: Gmail (Easiest)

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=<app-specific-password>
```

**Setup App Password:**
1. Google Account → Security
2. 2-Step Verification (enable if not already)
3. App passwords → Generate
4. Use generated password

**Limit:** 500 emails/day

### Option 2: SendGrid (Better)

Free tier: 100 emails/day forever

1. Sign up: https://sendgrid.com/free
2. Get API key
3. Configure:
```bash
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=<your-sendgrid-api-key>
```

---

## 🎓 Learning Resources

After deployment, learn more:

- **Render Docs**: https://render.com/docs
- **Fly.io Docs**: https://fly.io/docs
- **FastAPI Deployment**: https://fastapi.tiangolo.com/deployment/

---

## 🆘 Troubleshooting

### App won't start on Render

**Check build logs** in Render dashboard:
- Click your service → "Logs" tab
- Look for Python errors

**Common issues:**
- Missing `requirements.txt` dependencies
- Wrong `WORKDIR` path in commands
- Database connection string format

**Solution:**
```yaml
# In render.yaml, ensure paths are correct:
buildCommand: |
  cd face_attendance_fastapi
  pip install -r requirements.txt
```

### Database connection error

**Render:**
- Database URL is auto-injected
- Check: Dashboard → Environment → `DATABASE_URL`

**Fly.io:**
```bash
flyctl postgres list
flyctl secrets list
```

### Port binding error

Apps must listen on `$PORT` environment variable:

**Render/Railway:** Sets `PORT` automatically
**Fly.io:** Set in `fly.toml`

Our Dockerfile already uses:
```bash
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 📝 Next Steps After Deployment

1. **Test your API**:
   ```bash
   curl https://your-app.onrender.com/api/health
   ```

2. **Create admin user**:
   - Use Render Shell: Dashboard → Shell tab
   ```bash
   python scripts/db_manager.py seed
   ```

3. **Setup monitoring**:
   - Use UptimeRobot (free) to monitor uptime
   - Check Render logs regularly

4. **Add custom domain** (optional):
   - Render: Dashboard → Settings → Custom Domain
   - Point your domain's CNAME to Render URL

---

## 💰 Cost Breakdown

**Completely FREE Setup:**

- ✅ Hosting: Render.com (free tier)
- ✅ Database: PostgreSQL on Render (free tier)
- ✅ SSL Certificate: Automatic (free)
- ✅ Email: Gmail/SendGrid free tier
- ✅ Monitoring: UptimeRobot (free)
- ✅ Domain: Freenom (free .tk/.ml) or use Render subdomain

**Total monthly cost: $0** 🎉

**Optional paid upgrades:**
- Custom domain: ~$12/year (Google Domains, Namecheap)
- Render paid tier: $7/month (no sleep, better performance)
- Fly.io beyond free: ~$5-10/month for more resources

---

## 🎉 You're Ready!

**Recommended deployment path:**

1. **Start with Render.com** (easiest, 5 minutes)
2. **If you like it but want always-on** → Upgrade to Render paid ($7/mo) or switch to Fly.io
3. **For long-term serious project** → Oracle Cloud Always Free

**First deployment is the hardest. You've got this!** 🚀

Need help with any step? Just ask!
