# DigitalOcean Deployment Guide (GitHub Student Pack)

Deploy your FastAPI app on DigitalOcean using your **$200 free credit** from GitHub Student Pack!

---

## 🎓 Claim Your Student Benefits

1. Go to https://education.github.com/pack
2. Verify you're still eligible
3. Find **DigitalOcean** in the offers
4. Click "Get access to DigitalOcean"
5. You'll get **$200 credit for 1 year**

---

## 🚀 Option A: App Platform (5 Minutes - Easiest)

**Like Render, but better with your credits!**

### Step 1: Prepare GitHub Repo

Update `.do/app.yaml` with your GitHub info:

```bash
cd face_attendance_fastapi
nano .do/app.yaml

# Change these lines:
# repo: YOUR_GITHUB_USERNAME/YOUR_REPO_NAME
# To your actual GitHub username/repo
```

### Step 2: Push to GitHub

```bash
git add .do/app.yaml
git commit -m "feat: add DigitalOcean App Platform config"
git push
```

### Step 3: Deploy on DigitalOcean

1. Go to https://cloud.digitalocean.com/apps
2. Click **"Create App"**
3. Choose **"GitHub"** as source
4. Select your repository
5. DigitalOcean detects `.do/app.yaml` automatically
6. Click **"Next"** through the steps
7. Review (should show $12/month but covered by credits)
8. Click **"Create Resources"**

### Step 4: Configure Secrets

After deployment starts:

1. Go to your app → **Settings** → **App-Level Environment Variables**
2. Click **"Edit"**
3. Add encrypted variable:
   ```
   SECRET_KEY = <generate-with-command-below>
   ```
4. Click **"Save"**

Generate secret key:
```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### Step 5: Access Your App

Your app will be live at:
```
https://face-attendance-api-xxxxx.ondigitalocean.app
```

---

## 💻 Option B: Droplet (Full Control)

**For $4-6/month (40+ months with $200 credit!)**

### Step 1: Create Droplet

1. Go to https://cloud.digitalocean.com/droplets/new
2. Choose:
   - **Image**: Docker on Ubuntu 22.04 (Marketplace)
   - **Plan**: Basic ($4/month or $6/month)
   - **Datacenter**: Closest to you
   - **Authentication**: SSH Key (create one if needed)
   - **Hostname**: attendance-api
3. Click **"Create Droplet"**

### Step 2: SSH into Droplet

```bash
ssh root@YOUR_DROPLET_IP
```

### Step 3: Setup Application

```bash
# Clone your repository
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO/face_attendance_fastapi

# Create environment file
cat > .env.production << 'EOF'
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
DATABASE_URL=postgresql+asyncpg://attendance:PASSWORD@localhost/attendance_db
ENVIRONMENT=production
DEBUG=False
EOF

# Install PostgreSQL
apt update
apt install -y postgresql postgresql-contrib

# Create database
sudo -u postgres psql -c "CREATE DATABASE attendance_db;"
sudo -u postgres psql -c "CREATE USER attendance WITH PASSWORD 'YourSecurePassword';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE attendance_db TO attendance;"

# Update DATABASE_URL in .env.production with the password

# Start with Docker Compose
docker compose -f docker-compose.yml up -d

# Run migrations
docker compose exec api alembic upgrade head

# Seed initial data
docker compose exec api python scripts/db_manager.py seed
```

### Step 4: Configure Firewall

```bash
# Allow HTTP, HTTPS, SSH
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

### Step 5: Setup Domain & SSL (Optional)

**Free domain from Student Pack:** You get a free `.me` domain from Namecheap!

1. Claim at https://nc.me (GitHub Student Pack)
2. Point A record to your droplet IP
3. Install SSL:

```bash
# Install Certbot
apt install -y certbot python3-certbot-nginx nginx

# Get certificate
certbot --nginx -d yourdomain.me

# Auto-renewal
certbot renew --dry-run
```

### Step 6: Setup Nginx Reverse Proxy

Create `/etc/nginx/sites-available/attendance`:

```nginx
server {
    listen 80;
    server_name yourdomain.me;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and restart:
```bash
ln -s /etc/nginx/sites-available/attendance /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

---

## 📊 Cost Breakdown with $200 Credit

| Option | Monthly Cost | Months with $200 | Features |
|--------|--------------|------------------|----------|
| **App Platform** (basic-xxs + db) | ~$12 | **16 months** | Auto-deploy, managed DB, SSL |
| **Droplet** ($6) + Managed DB ($15) | ~$21 | 9 months | Full control |
| **Droplet** ($6) + Self-hosted DB | ~$6 | **33 months!** | Most economical |

**Recommended:** App Platform for ease, or Droplet for cost savings!

---

## 🎓 Other Student Pack Options

### Azure ($100 Credit)

```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Login
az login

# Create resources
az group create --name attendance-rg --location eastus
az postgres server create --resource-group attendance-rg \
  --name attendance-db --sku-name B_Gen5_1

# Deploy container
az container create --resource-group attendance-rg \
  --name attendance-api \
  --image YOUR_DOCKER_HUB_USERNAME/attendance-api \
  --dns-name-label attendance-api \
  --ports 8000
```

### Railway ($5/month credit)

Railway also works great with students:

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

---

## 🛠️ Troubleshooting

### App Platform Issues

**Build fails:**
- Check logs in DigitalOcean dashboard
- Verify Dockerfile path in app.yaml
- Ensure all environment variables are set

**Database connection error:**
- DATABASE_URL is auto-injected as `${db.DATABASE_URL}`
- Check in Settings → Environment Variables

**App crashes on startup:**
```bash
# View logs
doctl apps logs YOUR_APP_ID

# Check health endpoint
curl https://your-app.ondigitalocean.app/api/health
```

### Droplet Issues

**Can't connect:**
```bash
# Check firewall
ufw status

# Check if app is running
docker ps
```

**Database connection fails:**
```bash
# Check PostgreSQL is running
systemctl status postgresql

# Test connection
psql -U attendance -d attendance_db
```

---

## 📱 Monitoring & Maintenance

### App Platform

- **Logs**: Dashboard → Your App → Logs
- **Metrics**: Dashboard → Your App → Insights
- **Alerts**: Set up in Monitoring section

### Droplet

```bash
# View app logs
docker compose logs -f

# Monitor resources
htop

# Check disk space
df -h

# Database backup
pg_dump -U attendance attendance_db | gzip > backup.sql.gz
```

---

## 🎉 Your App is Live!

**App Platform URL:**
```
https://face-attendance-api-xxxxx.ondigitalocean.app
```

**Droplet with domain:**
```
https://yourdomain.me
```

**API Docs:**
```
https://your-app/api/docs
```

**Create admin user:**
```bash
# App Platform
doctl apps exec YOUR_APP_ID -- python scripts/db_manager.py seed

# Droplet
docker compose exec api python scripts/db_manager.py seed
```

---

## 💰 Managing Your Credits

Track usage:
1. Go to https://cloud.digitalocean.com/billing
2. Monitor "Current Balance"
3. You have **$200 for 1 year**
4. Set up billing alerts

---

## 🔗 Useful Links

- **DigitalOcean Dashboard**: https://cloud.digitalocean.com
- **Student Pack**: https://education.github.com/pack
- **Namecheap Domain**: https://nc.me (free .me domain)
- **App Platform Docs**: https://docs.digitalocean.com/products/app-platform/
- **Droplet Docs**: https://docs.digitalocean.com/products/droplets/

---

**Need help?** DigitalOcean has great student-focused support! 🚀
