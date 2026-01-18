# What You Need to Configure Before Deployment

This is a quick checklist of values YOU need to provide before deploying to production.

## ✅ Implementation Status

**All production-readiness features have been implemented!** 

The system is now secure, scalable, and ready for deployment. However, you need to provide your specific configuration values.

---

## 🔧 Required Configuration (Before First Deployment)

### 1. Environment Variables (.env file)

Copy `.env.example` to `.env` and update these values:

```bash
cp .env.example .env
```

Then edit `.env`:

#### **CRITICAL - Must Change:**
- [ ] **SECRET_KEY**: Generate with `python -c "import secrets; print(secrets.token_hex(32))"`
- [ ] **POSTGRES_PASSWORD**: Choose a strong password (20+ characters recommended)
- [ ] **DATABASE_URL**: Update with your PostgreSQL password (same as above)

#### **Optional - Can Keep Defaults:**
- [ ] FLASK_ENV=production *(keep as-is)*
- [ ] DB_POOL_SIZE=10 *(adjust based on expected load)*
- [ ] SESSION_LIFETIME=3600 *(1 hour, adjust if needed)*
- [ ] LOG_LEVEL=INFO *(keep as-is for production)*

### 2. Docker Compose Production File

Edit `docker-compose.prod.yml`:

- [ ] **Line 36**: Replace `your-domain.com` with your actual domain name
  ```yaml
  - "traefik.http.routers.arma3-tracker.rule=Host(`your-actual-domain.com`)"
  ```

### 3. Traefik Setup

Ensure Traefik is configured:

- [ ] Traefik reverse proxy is installed and running
- [ ] Traefik is configured for Let's Encrypt (or your TLS provider)
- [ ] Traefik network exists: `docker network create traefik_network`
- [ ] Traefik can access Docker socket (`/var/run/docker.sock`)

### 4. Server Prerequisites

- [ ] Docker and Docker Compose installed
- [ ] Port 443 is open (for HTTPS)
- [ ] DNS is configured (your-domain.com points to your server)
- [ ] Sufficient disk space (at least 10GB free recommended)

---

## 📋 Deployment Decision Points

### Image Source

Choose ONE approach:

**Option A: Pre-Built Images from GHCR (Recommended)**
- ✅ Faster deployment (no build time)
- ✅ Consistent builds
- ✅ Easy version management
- Use `docker-compose.ghcr.yml`
- Images automatically built on release
- See [GHCR.md](GHCR.md) for details

**Option B: Build Locally**
- ✅ No external dependencies
- ✅ Works offline
- Use `docker-compose.prod.yml`
- Builds image on your server

### Database Migration Strategy

Choose ONE approach:

**Option A: Fresh Database (Recommended if no data exists)**
```bash
# Use docker-compose.ghcr.yml or docker-compose.prod.yml
docker-compose -f docker-compose.ghcr.yml exec web flask db init
docker-compose -f docker-compose.ghcr.yml exec web flask db migrate -m "Initial migration"
docker-compose -f docker-compose.ghcr.yml exec web flask db upgrade
```

**Option B: Existing Database (If you have data from init.sql)**
```bash
# Just stamp the database as current
docker-compose -f docker-compose.ghcr.yml exec web flask db stamp head
```

### Rate Limiting Storage

Choose ONE:

**Option A: Memory Storage (Simple, Single Instance)**
- Default configuration
- Already configured
- No additional setup needed
- ⚠️ Rate limits reset on container restart

**Option B: Redis Storage (Distributed, Multi-Instance)**
- Requires Redis container
- Better for multiple app instances
- Persistent rate limiting
- Add to docker-compose.prod.yml:
  ```yaml
  redis:
    image: redis:7-alpine
    restart: unless-stopped
  ```
- Update .env:
  ```bash
  REDIS_URL=redis://redis:6379/0
  ```

### Backup Strategy

Choose your approach:

**Option A: Manual Backups**
- Run: `docker-compose -f docker-compose.prod.yml exec db pg_dump -U postgres asset_tracker > backup.sql`
- Schedule via cron job

**Option B: Automated Backups**
- Add backup container to docker-compose
- Use pgBackRest or similar tool
- Configure backup schedule

**Option C: Cloud Database**
- Use managed PostgreSQL (AWS RDS, Google Cloud SQL, etc.)
- Built-in backups
- Point DATABASE_URL to cloud database

---

## 🚀 Quick Start Commands

Once you've configured the above:

```bash
# 1. Create .env with your values
cp .env.example .env
# Edit .env with your actual values

# 2. Use the automated setup script
chmod +x setup_production.sh
./setup_production.sh

# Or on Windows:
setup_production.bat
```

OR manually:

```bash
# 1. Create Docker network
docker network create traefik_network

# 2. Deploy
docker-compose -f docker-compose.prod.yml up -d --build

# 3. Setup database
docker-compose -f docker-compose.prod.yml exec web flask db init
docker-compose -f docker-compose.prod.yml exec web flask db migrate -m "Initial"
docker-compose -f docker-compose.prod.yml exec web flask db upgrade

# 4. Create admin user
docker-compose -f docker-compose.prod.yml exec web python create_admin.py

# 5. Verify
curl https://your-domain.com/health
```

---

## ✨ What's Already Implemented (You Don't Need to Do)

✅ **Security:**
- CSRF protection
- Rate limiting
- Secure session cookies
- Security headers (HSTS, CSP, etc.)
- Non-root container user

✅ **Production Configuration:**
- Environment-based config
- Debug mode disabled in production
- Secrets externalized
- Database connection pooling

✅ **Monitoring:**
- Health check endpoints (/health, /ready)
- Structured logging with rotation
- Error pages (404, 500, 403)

✅ **Docker:**
- Production-optimized Dockerfile
- Production docker-compose with Traefik labels
- Container health checks
- Restart policies

✅ **Database:**
- Flask-Migrate integration
- Migration scripts ready
- Comprehensive migration guide

✅ **Documentation:**
- Complete README
- Deployment checklist
- Migration guide
- Quick reference
- Setup scripts

---

## 📝 After Deployment Checklist

Once deployed, verify:

- [ ] Application loads at https://your-domain.com
- [ ] SSL certificate is valid (check in browser)
- [ ] Health check responds: `curl https://your-domain.com/health`
- [ ] Can login with admin credentials
- [ ] Admin dashboard is accessible
- [ ] Can create a test campaign
- [ ] Logs are being written to `./logs/app.log`
- [ ] Security headers present (check with browser dev tools)
- [ ] Rate limiting works (try failing login 6+ times)

---

## 🆘 Need Help?

Refer to:
1. **DEPLOYMENT.md** - Complete deployment checklist
2. **README.md** - Full documentation
3. **MIGRATIONS.md** - Database migration guide
4. **QUICKREF.md** - Quick command reference
5. **PRODUCTION_READINESS.md** - What was implemented

---

## Summary

**What YOU need to provide:**
1. Secret key (generate it)
2. PostgreSQL password (choose it)
3. Your domain name (update in docker-compose.prod.yml)
4. Traefik setup (ensure it's running)

**Everything else is already implemented and ready to go!**

Run `setup_production.sh` (or `.bat` on Windows) to get started quickly.
