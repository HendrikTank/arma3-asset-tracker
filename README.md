# ARMA3 Asset Tracker

A comprehensive web application for tracking and managing ARMA3 campaign assets, missions, and events. Built with Flask and PostgreSQL, designed for production deployment behind Traefik reverse proxy.

[![Docker Image](https://img.shields.io/badge/docker-ghcr.io-blue)](https://github.com/HendrikTank/arma3-asset-tracker/pkgs/container/arma3-asset-tracker)
[![Release](https://img.shields.io/github/v/release/HendrikTank/arma3-asset-tracker)](https://github.com/HendrikTank/arma3-asset-tracker/releases)
[![License](https://img.shields.io/github/license/HendrikTank/arma3-asset-tracker)](LICENSE)

## Features

- **Campaign Management**: Track multiple ARMA3 campaigns with detailed asset tracking
- **Asset Tracking**: Monitor vehicles, equipment, and resources across missions
- **Event Logging**: Comprehensive event tracking for campaign activities
- **Role-Based Access Control**: Admin, Manager, and Public user roles
- **Report Generation**: Generate and export campaign reports
- **Production Ready**: Security hardened with CSRF protection, rate limiting, and security headers
- **CI/CD Ready**: Automatic Docker image builds on release

## Architecture

- **Backend**: Flask 3.1.2 with SQLAlchemy ORM
- **Database**: PostgreSQL 15
- **WSGI Server**: Waitress (production) / Flask dev server (development)
- **Authentication**: Flask-Login with secure password hashing
- **Security**: CSRF protection, rate limiting, security headers (Flask-Talisman)
- **Migrations**: Flask-Migrate for database schema management

## Prerequisites

- Docker and Docker Compose
- Traefik reverse proxy (for production)
- Python 3.11+ (for local development)
- PostgreSQL 15+ (for local development without Docker)

## Quick Start (Development)

1. **Clone the repository**
   ```bash
   git clone https://github.com/HendrikTank/arma3-asset-tracker.git
   cd arma3-asset-tracker
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start with Docker Compose**
   ```bash
   docker-compose up -d
   ```

4. **Create admin user**
   ```bash
   docker-compose exec web python create_admin.py
   ```

5. **Access the application**
   - Open http://localhost:5000
   - Login with your admin credentials

## Production Deployment

### Requirements

- Traefik reverse proxy with TLS/SSL certificates
- Secure environment variable management
- PostgreSQL backup strategy
- Log aggregation system (optional but recommended)

### Production Setup

#### Option A: Using Pre-Built Images (Recommended)

Use pre-built Docker images from GitHub Container Registry for faster deployment:

1. **Prepare environment variables**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` with production values:
   ```bash
   # Generate secure secret key
   python -c "import secrets; print(secrets.token_hex(32))"
   
   # Update .env
   FLASK_ENV=production
   SECRET_KEY=<generated-secret-key>
   DATABASE_URL=postgresql://user:password@db:5432/asset_tracker
   POSTGRES_PASSWORD=<secure-database-password>
   ```

2. **Configure Traefik labels**
   
   Edit `docker-compose.ghcr.yml` and update Traefik labels:
   ```yaml
   labels:
     - "traefik.http.routers.arma3-tracker.rule=Host(`your-domain.com`)"
     # Update your-domain.com with your actual domain
   ```

3. **Create Docker networks**
   ```bash
   # Create Traefik network if it doesn't exist
   docker network create traefik_network
   ```

4. **Deploy the application**
   ```bash
   # Pull and start containers (no build needed!)
   docker-compose -f docker-compose.ghcr.yml pull
   docker-compose -f docker-compose.ghcr.yml up -d
   
   # Check logs
   docker-compose -f docker-compose.ghcr.yml logs -f web
   ```

5. **Continue with steps 5-7 below**

#### Option B: Building Locally

Build the Docker image on your server:

1. **Prepare environment variables** (same as Option A)

2. **Configure Traefik labels**
   
   Edit `docker-compose.prod.yml` and update Traefik labels:
   ```yaml
   labels:
     - "traefik.http.routers.arma3-tracker.rule=Host(`your-domain.com`)"
     # Update your-domain.com with your actual domain
   ```

3. **Create Docker networks**
   ```bash
   # Create Traefik network if it doesn't exist
   docker network create traefik_network
   ```

4. **Deploy the application**
   ```bash
   # Build and start containers
   docker-compose -f docker-compose.prod.yml up -d --build
   
   # Check logs
   docker-compose -f docker-compose.prod.yml logs -f web
   ```

5. **Run database migrations**
   ```bash
   docker-compose -f docker-compose.prod.yml exec web flask db upgrade
   ```

6. **Create admin user**
   ```bash
   docker-compose -f docker-compose.prod.yml exec web python create_admin.py
   ```

7. **Verify deployment**
   - Check health endpoint: `https://your-domain.com/health`
   - Check readiness: `https://your-domain.com/ready`
   - Login at: `https://your-domain.com/auth/login`

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FLASK_ENV` | Yes | production | Environment: development, production, testing |
| `SECRET_KEY` | Yes | - | Flask secret key (generate securely!) |
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `POSTGRES_USER` | Yes | postgres | PostgreSQL username |
| `POSTGRES_PASSWORD` | Yes | - | PostgreSQL password |
| `POSTGRES_DB` | Yes | asset_tracker | Database name |
| `DB_POOL_SIZE` | No | 10 | Database connection pool size |
| `DB_POOL_RECYCLE` | No | 3600 | Connection recycle time (seconds) |
| `DB_MAX_OVERFLOW` | No | 20 | Maximum overflow connections |
| `SESSION_COOKIE_SECURE` | No | True | Require HTTPS for session cookies |
| `SESSION_LIFETIME` | No | 3600 | Session lifetime (seconds) |
| `LOG_LEVEL` | No | INFO | Logging level: DEBUG, INFO, WARNING, ERROR |
| `LOG_FORMAT` | No | json | Log format: json or text |
| `MAX_CONTENT_LENGTH` | No | 16777216 | Max upload size (bytes) |

### Database Migrations

This application uses Flask-Migrate for database schema management:

```bash
# Initialize migrations (first time only, already done)
flask db init

# Create a new migration after model changes
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade

# Rollback one migration
flask db downgrade

# View migration history
flask db history
```

In Docker:
```bash
docker-compose -f docker-compose.prod.yml exec web flask db upgrade
```

### CI/CD and Container Registry

This project uses GitHub Actions to automatically build and publish Docker images to GitHub Container Registry (ghcr.io) on every release.

**Automatic Builds:**
- Create a GitHub release (e.g., `v1.0.0`)
- GitHub Actions automatically builds the image
- Image is pushed to `ghcr.io/henriktank/arma3-asset-tracker`
- Tagged as: `v1.0.0`, `v1.0`, `v1`, `latest`

**Using Pre-Built Images:**
```bash
# Pull latest image
docker pull ghcr.io/henriktank/arma3-asset-tracker:latest

# Or specific version
docker pull ghcr.io/henriktank/arma3-asset-tracker:v1.0.0

# Deploy with docker-compose.ghcr.yml
docker-compose -f docker-compose.ghcr.yml up -d
```

**Benefits:**
- ✅ No build time on server
- ✅ Faster deployments
- ✅ Consistent builds across environments
- ✅ Easy rollbacks to previous versions

For detailed information, see [GHCR.md](GHCR.md).

### Security Considerations

1. **Secrets Management**
   - Never commit `.env` file to version control
   - Use strong, randomly generated secrets
   - Rotate secrets regularly
   - Consider using Docker secrets or external secret managers

2. **HTTPS/TLS**
   - Application must be behind Traefik with TLS termination
   - `SESSION_COOKIE_SECURE=True` requires HTTPS
   - Security headers enforced by Flask-Talisman

3. **Rate Limiting**
   - Login endpoint limited to 5 attempts per minute
   - Global limits: 200/day, 50/hour per IP
   - Consider Redis for distributed rate limiting

4. **Database Security**
   - Use strong PostgreSQL passwords
   - Database not exposed externally (internal network only)
   - Regular backup schedule required

### Traefik Integration

The application is designed to work behind Traefik reverse proxy:

**Traefik Configuration**:
- TLS termination handled by Traefik
- Health checks on `/health` endpoint
- Headers forwarding configured
- HTTPS redirect enabled

**Required Traefik Setup**:
```yaml
# Example Traefik docker-compose.yml snippet
services:
  traefik:
    image: traefik:v2.10
    command:
      - "--providers.docker=true"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.email=your-email@domain.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
      - "--certificatesresolvers.letsencrypt.acme.tlschallenge=true"
    ports:
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - traefik-certificates:/letsencrypt
    networks:
      - traefik_network
```

### Monitoring and Logging

**Application Logs**:
- Logs written to `/app/logs/app.log` in container
- Mounted to `./logs/` on host for persistence
- JSON format for structured logging in production
- Automatic log rotation (10MB max, 10 backups)

**Health Checks**:
- `/health` - Basic application health (returns 200)
- `/ready` - Database connectivity check (returns 200 or 503)
- Docker healthcheck configured
- Traefik uses `/health` for load balancer health checks

**Monitoring Integration**:
- Add Prometheus metrics endpoint (future enhancement)
- Integrate with error tracking (Sentry, Rollbar)
- Set up log aggregation (ELK, Loki, CloudWatch)

### Backup and Recovery

**Database Backup**:
```bash
# Backup database
docker-compose -f docker-compose.prod.yml exec db pg_dump -U postgres asset_tracker > backup.sql

# Restore database
docker-compose -f docker-compose.prod.yml exec -T db psql -U postgres asset_tracker < backup.sql
```

**Automated Backup Strategy**:
1. Set up cron job for daily backups
2. Store backups in separate location
3. Test restore procedure regularly
4. Keep multiple backup generations

**Reports and Uploads**:
- Reports stored in `./reports/` directory (mounted volume)
- Back up reports directory regularly
- Consider object storage (S3, MinIO) for production

### Troubleshooting

**Application won't start**:
```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs web

# Check database connection
docker-compose -f docker-compose.prod.yml exec web flask db current

# Verify environment variables
docker-compose -f docker-compose.prod.yml exec web env | grep FLASK
```

**Database connection errors**:
```bash
# Check database status
docker-compose -f docker-compose.prod.yml exec db pg_isready -U postgres

# Check DATABASE_URL format
# Should be: postgresql://user:password@db:5432/database_name
```

**Permission errors**:
```bash
# Fix logs directory permissions
chmod -R 755 logs/

# Fix reports directory permissions
chmod -R 755 reports/
```

**Session/Cookie issues**:
- Verify `SESSION_COOKIE_SECURE=True` only with HTTPS
- Check that cookies are not blocked by browser
- Verify Traefik is forwarding headers correctly

**Rate limiting issues**:
- Check if too many requests from same IP
- Wait for rate limit window to reset
- Consider adding Redis for better rate limiting

## Development

### Local Development Setup

1. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables**
   ```bash
   export FLASK_ENV=development
   export DATABASE_URL=postgresql://postgres:password@localhost/asset_tracker
   ```

4. **Run migrations**
   ```bash
   flask db upgrade
   ```

5. **Run development server**
   ```bash
   python wsgi.py
   ```

### Testing

```bash
# Run tests
python test_app.py

# With coverage
pytest --cov=app tests/
```

## Project Structure

```
arma3-asset-tracker/
├── app/
│   ├── __init__.py          # Application factory and configuration
│   ├── auth.py              # Authentication routes
│   ├── config.py            # Configuration classes
│   ├── models.py            # Database models
│   ├── routes.py            # Application routes
│   └── templates/           # Jinja2 templates
│       ├── base.html
│       ├── admin/          # Admin templates
│       ├── manager/        # Manager templates
│       ├── public/         # Public templates
│       └── errors/         # Error pages
├── reports/                 # Generated reports
├── logs/                    # Application logs
├── migrations/              # Database migrations
├── .env.example            # Example environment variables
├── .dockerignore           # Docker ignore patterns
├── .gitignore              # Git ignore patterns
├── create_admin.py         # Admin user creation script
├── docker-compose.yml      # Development compose file
├── docker-compose.prod.yml # Production compose file
├── Dockerfile              # Container definition
├── init.sql                # Initial database schema
├── requirements.txt        # Python dependencies
├── test_app.py            # Test suite
└── wsgi.py                # WSGI entry point
```

## User Roles

- **Admin**: Full system access, user management, all campaigns
- **Manager**: Campaign management, asset tracking, reports
- **Public**: Read-only access to public dashboards

## Support

For issues and questions:
- GitHub Issues: https://github.com/HendrikTank/arma3-asset-tracker/issues
- Documentation: See this README

## License

See [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

**Security Notice**: Always use HTTPS in production, keep secrets secure, and follow security best practices.