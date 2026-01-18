# Production Deployment Checklist

Use this checklist to ensure all critical steps are completed before deploying to production.

## Pre-Deployment Preparation

### 1. Environment Configuration

- [ ] Copy `.env.example` to `.env`
- [ ] Generate secure `SECRET_KEY` (use: `python -c "import secrets; print(secrets.token_hex(32))"`)
- [ ] Set `FLASK_ENV=production`
- [ ] Configure `DATABASE_URL` with production credentials
- [ ] Set strong `POSTGRES_PASSWORD`
- [ ] Set `SESSION_COOKIE_SECURE=True`
- [ ] Configure appropriate `LOG_LEVEL` (INFO or WARNING)
- [ ] Review all environment variables in `.env.example`
- [ ] Ensure `.env` is in `.gitignore` and NOT committed to version control

### 2. Traefik Configuration

- [ ] Traefik reverse proxy is installed and running
- [ ] `traefik_network` Docker network exists (`docker network create traefik_network`)
- [ ] Update `docker-compose.prod.yml` with your domain name in Traefik labels
- [ ] Configure TLS/SSL certificate resolver (Let's Encrypt)
- [ ] Verify Traefik has access to Docker socket
- [ ] Test Traefik configuration: `docker-compose -f traefik-compose.yml config`

### 3. Security Review

- [ ] All secrets are environment variables (no hardcoded values)
- [ ] Secret key is randomly generated and secure (32+ characters)
- [ ] Database password is strong and unique
- [ ] CSRF protection is enabled (automatic in Flask-WTF)
- [ ] Rate limiting is configured on authentication endpoints
- [ ] Security headers are configured (Flask-Talisman)
- [ ] Session cookies are secure (`SESSION_COOKIE_SECURE=True`)
- [ ] Application runs as non-root user in container
- [ ] Database is not exposed to public internet
- [ ] `.env` file has restricted permissions (`chmod 600 .env`)

### 4. Database Setup

- [ ] PostgreSQL backup strategy is defined
- [ ] Database migration plan is ready
- [ ] Test database restore procedure
- [ ] Connection pooling is configured appropriately
- [ ] Database volume persistence is configured
- [ ] Database credentials are secured

### 5. Docker Configuration

- [ ] Review `docker-compose.prod.yml` configuration
- [ ] Remove or comment out development-only settings
- [ ] Verify no development volumes are mounted (except reports, logs)
- [ ] Container restart policies are set (`restart: unless-stopped`)
- [ ] Health checks are configured for all services
- [ ] Resource limits are defined (optional but recommended)
- [ ] Networks are properly configured (internal vs external)

### 6. Application Configuration

- [ ] Debug mode is disabled (`DEBUG=False` in production config)
- [ ] Error handlers are implemented (404, 500, 403)
- [ ] Health check endpoints work (`/health`, `/ready`)
- [ ] Logging is configured for production
- [ ] Log rotation is set up
- [ ] Reports directory is writable
- [ ] Logs directory is writable

## Deployment Steps

### 1. Initial Deployment

- [ ] Clone repository to production server
- [ ] Create `.env` file with production values
- [ ] Build Docker images: `docker-compose -f docker-compose.prod.yml build`
- [ ] Review build output for errors
- [ ] Start services: `docker-compose -f docker-compose.prod.yml up -d`
- [ ] Check container status: `docker-compose -f docker-compose.prod.yml ps`
- [ ] Review logs: `docker-compose -f docker-compose.prod.yml logs -f`

### 2. Database Migration

- [ ] Verify database container is healthy
- [ ] Initialize Flask-Migrate (first time): `docker-compose -f docker-compose.prod.yml exec web flask db init`
- [ ] Create initial migration: `docker-compose -f docker-compose.prod.yml exec web flask db migrate -m "Initial migration"`
- [ ] Review generated migration in `migrations/versions/`
- [ ] Apply migration: `docker-compose -f docker-compose.prod.yml exec web flask db upgrade`
- [ ] Verify migration: `docker-compose -f docker-compose.prod.yml exec web flask db current`

### 3. Initial Data Setup

- [ ] Create admin user: `docker-compose -f docker-compose.prod.yml exec web python create_admin.py`
- [ ] Test admin login
- [ ] Create initial campaigns/assets if needed
- [ ] Verify database entries

### 4. Application Testing

- [ ] Access application via domain (https://your-domain.com)
- [ ] Verify HTTPS redirect works
- [ ] Test health endpoint: `curl https://your-domain.com/health`
- [ ] Test readiness endpoint: `curl https://your-domain.com/ready`
- [ ] Login with admin credentials
- [ ] Test admin dashboard access
- [ ] Test creating/editing campaigns
- [ ] Test creating/editing assets
- [ ] Test report generation
- [ ] Verify all role-based permissions work
- [ ] Test logout functionality
- [ ] Test rate limiting on login (intentionally fail 5+ times)

### 5. Monitoring Setup

- [ ] Verify application logs are being written: `ls -la logs/`
- [ ] Test log rotation (optional: wait or trigger)
- [ ] Check Docker logs: `docker-compose -f docker-compose.prod.yml logs --tail=100`
- [ ] Verify health checks pass in Traefik dashboard
- [ ] Set up external monitoring (uptime monitor, status page)
- [ ] Configure alerts for application down/errors

## Post-Deployment Verification

### 1. Security Verification

- [ ] Run SSL test: https://www.ssllabs.com/ssltest/
- [ ] Verify security headers: https://securityheaders.com/
- [ ] Test CSP (Content Security Policy) is working
- [ ] Verify cookies have Secure and HttpOnly flags
- [ ] Test HTTPS enforcement (HTTP should redirect to HTTPS)
- [ ] Verify database port is not exposed: `nmap your-server-ip`

### 2. Performance Testing

- [ ] Test application response time
- [ ] Verify database connection pooling is working
- [ ] Test concurrent user access
- [ ] Monitor memory usage: `docker stats`
- [ ] Check CPU usage under load
- [ ] Test with expected user load

### 3. Backup Verification

- [ ] Create first manual backup
  ```bash
  docker-compose -f docker-compose.prod.yml exec db pg_dump -U postgres asset_tracker > backup_initial.sql
  ```
- [ ] Test backup restore on test database
- [ ] Set up automated backup cron job
- [ ] Verify backup storage location
- [ ] Document backup retention policy

### 4. Documentation

- [ ] Document deployment date and version
- [ ] Document all environment variables used
- [ ] Create runbook for common operations
- [ ] Document rollback procedure
- [ ] Create troubleshooting guide
- [ ] Share admin credentials securely with team
- [ ] Document monitoring and alerting setup

## Ongoing Maintenance

### Daily

- [ ] Check application health status
- [ ] Review error logs for critical issues
- [ ] Monitor disk space usage

### Weekly

- [ ] Review application logs for warnings/errors
- [ ] Check database backup integrity
- [ ] Review security logs (if available)
- [ ] Monitor resource usage trends

### Monthly

- [ ] Update dependencies (test in staging first)
- [ ] Review and rotate logs if needed
- [ ] Test backup restore procedure
- [ ] Review security updates
- [ ] Update SSL certificates (if not automated)

### As Needed

- [ ] Apply database migrations for schema changes
- [ ] Update application code
- [ ] Scale resources if needed
- [ ] Review and optimize database queries
- [ ] Update documentation

## Emergency Procedures

### Application Not Starting

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs web

# Check database connection
docker-compose -f docker-compose.prod.yml exec web flask db current

# Restart services
docker-compose -f docker-compose.prod.yml restart
```

### Database Connection Issues

```bash
# Check database health
docker-compose -f docker-compose.prod.yml exec db pg_isready -U postgres

# Restart database
docker-compose -f docker-compose.prod.yml restart db

# Check connection string
docker-compose -f docker-compose.prod.yml exec web env | grep DATABASE_URL
```

### Rollback Deployment

```bash
# Stop services
docker-compose -f docker-compose.prod.yml down

# Restore database backup
docker-compose -f docker-compose.prod.yml up -d db
docker-compose -f docker-compose.prod.yml exec -T db psql -U postgres asset_tracker < backup_YYYYMMDD.sql

# Deploy previous version
git checkout <previous-tag>
docker-compose -f docker-compose.prod.yml up -d --build

# Verify
docker-compose -f docker-compose.prod.yml logs -f
```

### Certificate Issues

```bash
# Check certificate expiry
openssl s_client -connect your-domain.com:443 -servername your-domain.com | openssl x509 -noout -dates

# Force certificate renewal (Traefik + Let's Encrypt)
docker-compose -f traefik-compose.yml restart traefik
```

## Contact Information

- **System Administrator**: [Name/Email]
- **Database Administrator**: [Name/Email]
- **Security Contact**: [Name/Email]
- **Emergency Contact**: [Phone]

## References

- Main README: [README.md](README.md)
- Migration Guide: [MIGRATIONS.md](MIGRATIONS.md)
- Traefik Documentation: https://doc.traefik.io/traefik/
- Flask Documentation: https://flask.palletsprojects.com/
- PostgreSQL Documentation: https://www.postgresql.org/docs/

---

**Last Updated**: 2026-01-18  
**Deployment Version**: 1.0.0  
**Reviewed By**: [Name]
