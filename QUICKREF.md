# Quick Reference - Production Deployment

## Deployment Commands

### First-Time Setup (Using Pre-Built Images - Recommended)
```bash
# 1. Create environment file
cp .env.example .env

# 2. Generate secure secret key
python -c "import secrets; print(secrets.token_hex(32))"
# Copy output to .env file as SECRET_KEY

# 3. Edit .env and docker-compose.ghcr.yml with your values

# 4. Create Docker network
docker network create traefik_network

# 5. Pull and deploy (no build needed!)
docker-compose -f docker-compose.ghcr.yml pull
docker-compose -f docker-compose.ghcr.yml up -d

# 6. Initialize database
docker-compose -f docker-compose.ghcr.yml exec web flask db init
docker-compose -f docker-compose.ghcr.yml exec web flask db migrate -m "Initial migration"
docker-compose -f docker-compose.ghcr.yml exec web flask db upgrade

# 7. Create admin user
docker-compose -f docker-compose.ghcr.yml exec web python create_admin.py
```

### First-Time Setup (Building Locally)
```bash
# Use docker-compose.prod.yml instead of docker-compose.ghcr.yml
# Replace "pull" with "build" in step 5
docker-compose -f docker-compose.prod.yml up -d --build
```

### Or use automated script:
```bash
# Linux/Mac
chmod +x setup_production.sh
./setup_production.sh

# Windows
setup_production.bat
```

## Container Registry Operations

### Pull Latest Image
```bash
docker pull ghcr.io/henriktank/arma3-asset-tracker:latest
```

### Deploy New Version
```bash
# Update image tag in docker-compose.ghcr.yml if needed
# Then:
docker-compose -f docker-compose.ghcr.yml pull
docker-compose -f docker-compose.ghcr.yml up -d
```

### Rollback to Previous Version
```bash
# Edit docker-compose.ghcr.yml and change image tag to previous version
# Example: ghcr.io/henriktank/arma3-asset-tracker:v1.0.0
docker-compose -f docker-compose.ghcr.yml pull
docker-compose -f docker-compose.ghcr.yml up -d
```

## Daily Operations

### View Logs
```bash
docker-compose -f docker-compose.ghcr.yml logs -f
docker-compose -f docker-compose.ghcr.yml logs -f web
docker-compose -f docker-compose.ghcr.yml logs -f db
```

### Restart Services
```bash
docker-compose -f docker-compose.prod.yml restart
docker-compose -f docker-compose.prod.yml restart web
```

### Check Status
```bash
docker-compose -f docker-compose.prod.yml ps
docker stats
```

### Database Backup
```bash
docker-compose -f docker-compose.prod.yml exec db pg_dump -U postgres asset_tracker > backup_$(date +%Y%m%d).sql
```

### Database Restore
```bash
docker-compose -f docker-compose.prod.yml exec -T db psql -U postgres asset_tracker < backup.sql
```

## Database Migrations

### After Model Changes
```bash
# 1. Create migration
docker-compose -f docker-compose.prod.yml exec web flask db migrate -m "Description"

# 2. Review migration
cat migrations/versions/xxxx_description.py

# 3. Apply migration
docker-compose -f docker-compose.prod.yml exec web flask db upgrade

# 4. Check current version
docker-compose -f docker-compose.prod.yml exec web flask db current
```

### Rollback
```bash
docker-compose -f docker-compose.prod.yml exec web flask db downgrade
```

## Updates and Maintenance

### Update Application Code
```bash
# 1. Pull changes
git pull

# 2. Rebuild
docker-compose -f docker-compose.prod.yml up -d --build

# 3. Apply migrations if any
docker-compose -f docker-compose.prod.yml exec web flask db upgrade

# 4. Restart
docker-compose -f docker-compose.prod.yml restart web
```

### Update Dependencies
```bash
# Edit requirements.txt, then:
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

## Troubleshooting

### Application Not Starting
```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs web

# Check environment
docker-compose -f docker-compose.prod.yml exec web env | grep -E "(FLASK|DATABASE|SECRET)"

# Restart
docker-compose -f docker-compose.prod.yml restart web
```

### Database Connection Issues
```bash
# Check database health
docker-compose -f docker-compose.prod.yml exec db pg_isready -U postgres

# Check DATABASE_URL
docker-compose -f docker-compose.prod.yml exec web env | grep DATABASE_URL

# Restart database
docker-compose -f docker-compose.prod.yml restart db
```

### Permission Issues
```bash
# Fix logs directory
sudo chown -R 1000:1000 logs/
chmod -R 755 logs/

# Fix reports directory
sudo chown -R 1000:1000 reports/
chmod -R 755 reports/
```

## Health Checks

### Manual Health Check
```bash
curl https://your-domain.com/health
# Should return: {"status":"healthy"}

curl https://your-domain.com/ready
# Should return: {"status":"ready","database":"connected"}
```

### Check SSL/TLS
```bash
curl -I https://your-domain.com
openssl s_client -connect your-domain.com:443 -servername your-domain.com
```

## Monitoring

### Resource Usage
```bash
docker stats --no-stream
df -h  # Disk usage
docker system df  # Docker disk usage
```

### Log Sizes
```bash
du -sh logs/
ls -lh logs/
```

## Emergency Procedures

### Complete Restart
```bash
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

### Restore from Backup
```bash
# Stop application
docker-compose -f docker-compose.prod.yml stop web

# Restore database
docker-compose -f docker-compose.prod.yml exec -T db psql -U postgres asset_tracker < backup.sql

# Start application
docker-compose -f docker-compose.prod.yml start web
```

### Clear All Data and Reset
```bash
# WARNING: This deletes all data!
docker-compose -f docker-compose.prod.yml down -v
docker-compose -f docker-compose.prod.yml up -d
# Re-run database migrations and create admin user
```

## Environment Variables Quick Ref

| Variable | Required | Example |
|----------|----------|---------|
| FLASK_ENV | Yes | production |
| SECRET_KEY | Yes | (64 char hex) |
| DATABASE_URL | Yes | postgresql://user:pass@db:5432/asset_tracker |
| POSTGRES_PASSWORD | Yes | (strong password) |
| SESSION_COOKIE_SECURE | No (default: True) | True |
| LOG_LEVEL | No (default: INFO) | INFO |

## File Locations

- **Application**: `/app` in container
- **Logs**: `./logs` on host, `/app/logs` in container
- **Reports**: `./reports` on host, `/app/reports` in container
- **Database**: Docker volume `postgres_data`
- **Config**: `.env` file (not in container)

## Important URLs

- **Application**: https://your-domain.com
- **Login**: https://your-domain.com/auth/login
- **Health**: https://your-domain.com/health
- **Ready**: https://your-domain.com/ready

## Documentation

- **README**: Full documentation
- **DEPLOYMENT**: Detailed checklist
- **MIGRATIONS**: Database migration guide
- **PRODUCTION_READINESS**: Implementation summary

## Support

For issues:
1. Check logs: `docker-compose -f docker-compose.prod.yml logs`
2. Review documentation in README.md, DEPLOYMENT.md
3. Check health endpoints
4. Verify environment variables
