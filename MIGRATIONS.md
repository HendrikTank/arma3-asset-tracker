# Database Migration Guide

This guide covers database schema management using Flask-Migrate.

## Overview

Flask-Migrate provides Alembic integration for handling database schema changes. It tracks changes to your models and generates migration scripts that can be applied or rolled back.

## Initial Setup (First Time Only)

If migrations haven't been initialized yet:

```bash
# In Docker
docker-compose -f docker-compose.prod.yml exec web flask db init

# Or locally
flask db init
```

This creates a `migrations/` directory with Alembic configuration.

## Migration Workflow

### 1. Create a Migration

After modifying models in `app/models.py`:

```bash
# Development
docker-compose exec web flask db migrate -m "Add new column to assets table"

# Production
docker-compose -f docker-compose.prod.yml exec web flask db migrate -m "Description of changes"

# Local
flask db migrate -m "Description of changes"
```

This generates a migration script in `migrations/versions/`.

### 2. Review the Migration

Always review the generated migration before applying:

```bash
# Check the latest migration file
ls -la migrations/versions/

# Review the content
cat migrations/versions/xxxx_description.py
```

Verify:
- The upgrade() function contains correct changes
- The downgrade() function can properly reverse the changes
- No unintended changes were detected

### 3. Apply the Migration

```bash
# Development
docker-compose exec web flask db upgrade

# Production
docker-compose -f docker-compose.prod.yml exec web flask db upgrade

# Local
flask db upgrade
```

### 4. Verify the Migration

```bash
# Check current migration version
flask db current

# View migration history
flask db history
```

## Common Operations

### Rollback a Migration

```bash
# Rollback one version
flask db downgrade

# Rollback to specific version
flask db downgrade <revision_id>

# Rollback to beginning
flask db downgrade base
```

### Upgrade to Specific Version

```bash
flask db upgrade <revision_id>
```

### View Migration Status

```bash
# Current version
flask db current

# Full history
flask db history

# Show specific migration
flask db show <revision_id>
```

### Create Empty Migration

For manual migrations or data migrations:

```bash
flask db revision -m "Manual data migration"
```

Edit the generated file to add custom SQL or data operations.

## Transitioning from db.create_all()

The application previously used `db.create_all()` to create tables. To transition:

### Step 1: Backup Current Database

```bash
docker-compose exec db pg_dump -U postgres asset_tracker > backup_before_migration.sql
```

### Step 2: Create Initial Migration

If your database already has tables:

```bash
# Mark the current schema as the baseline
docker-compose exec web flask db stamp head
```

If starting fresh:

```bash
# Generate initial migration from models
docker-compose exec web flask db migrate -m "Initial migration"
docker-compose exec web flask db upgrade
```

## Production Deployment Workflow

### Before Deployment

1. **Test migrations in staging**
   ```bash
   # In staging environment
   docker-compose -f docker-compose.prod.yml exec web flask db upgrade
   ```

2. **Backup production database**
   ```bash
   docker-compose -f docker-compose.prod.yml exec db pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

### During Deployment

1. **Put application in maintenance mode** (if needed)

2. **Apply migrations**
   ```bash
   docker-compose -f docker-compose.prod.yml exec web flask db upgrade
   ```

3. **Verify migration**
   ```bash
   docker-compose -f docker-compose.prod.yml exec web flask db current
   ```

4. **Restart application**
   ```bash
   docker-compose -f docker-compose.prod.yml restart web
   ```

5. **Remove maintenance mode**

### Rollback Procedure

If deployment fails:

```bash
# Stop the application
docker-compose -f docker-compose.prod.yml stop web

# Rollback migration
docker-compose -f docker-compose.prod.yml exec db psql -U $POSTGRES_USER $POSTGRES_DB < backup_YYYYMMDD_HHMMSS.sql

# Or use Flask-Migrate rollback
docker-compose -f docker-compose.prod.yml exec web flask db downgrade

# Restart with previous version
docker-compose -f docker-compose.prod.yml up -d web
```

## Best Practices

### 1. Always Backup Before Migrations

```bash
# Automated backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose -f docker-compose.prod.yml exec -T db pg_dump -U postgres asset_tracker > backups/backup_$DATE.sql
echo "Backup created: backup_$DATE.sql"
```

### 2. Test Migrations Locally First

```bash
# Create test database copy
docker-compose exec db createdb -U postgres -T asset_tracker asset_tracker_test

# Test migration on copy
DATABASE_URL=postgresql://postgres:password@db/asset_tracker_test flask db upgrade
```

### 3. Review Auto-Generated Migrations

Alembic's auto-detection isn't perfect. Always review:
- Column type changes
- Constraint additions/removals
- Index operations
- Data migrations

### 4. Use Descriptive Migration Messages

Good:
```bash
flask db migrate -m "Add asset_status enum and update asset table"
```

Bad:
```bash
flask db migrate -m "update models"
```

### 5. Keep Migrations Small

Don't bundle unrelated changes. Create separate migrations for:
- Schema changes
- Data migrations
- Index additions

### 6. Handle Data Migrations Carefully

For data transformations, create manual migrations:

```python
"""Data migration: normalize asset names

Revision ID: xxxx
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Use op.execute() for data operations
    op.execute("""
        UPDATE assets 
        SET name = TRIM(UPPER(name))
        WHERE name IS NOT NULL
    """)

def downgrade():
    # Provide meaningful downgrade
    pass  # Data migrations often can't be fully reversed
```

## Troubleshooting

### "Target database is not up to date"

```bash
# Check current version vs available migrations
flask db current
flask db heads

# Upgrade to latest
flask db upgrade head
```

### "Can't locate revision identified by 'xxxx'"

Migration history is out of sync:

```bash
# View all revisions
flask db history

# Stamp to specific version
flask db stamp <revision_id>
```

### Alembic Didn't Detect Changes

```bash
# Force create migration
flask db revision --autogenerate -m "Force migration"

# Or create empty and manually edit
flask db revision -m "Manual migration"
```

### Merge Conflicts in Migration Files

Multiple developers created migrations:

```bash
# View heads
flask db heads

# Merge migrations
flask db merge <revision1> <revision2> -m "Merge migrations"
```

### Migration Fails Midway

```bash
# Check database state
docker-compose exec db psql -U postgres asset_tracker

# Manually fix issues, then
flask db stamp <last_successful_revision>

# Fix the migration script and retry
flask db upgrade
```

## Migration File Structure

```python
"""Add asset_location column

Revision ID: abc123def456
Revises: previous_revision_id
Create Date: 2026-01-18 10:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'abc123def456'
down_revision = 'previous_revision_id'
branch_labels = None
depends_on = None

def upgrade():
    # Changes to apply
    op.add_column('assets', 
        sa.Column('location', sa.String(255), nullable=True)
    )

def downgrade():
    # Changes to reverse
    op.drop_column('assets', 'location')
```

## Automated Migration Scripts

### Pre-Deployment Check

```bash
#!/bin/bash
# check_migrations.sh

echo "Checking for pending migrations..."

PENDING=$(docker-compose -f docker-compose.prod.yml exec -T web flask db current | grep -o "[a-f0-9]*")
HEAD=$(docker-compose -f docker-compose.prod.yml exec -T web flask db heads | grep -o "[a-f0-9]*" | head -1)

if [ "$PENDING" != "$HEAD" ]; then
    echo "⚠️  Warning: Pending migrations detected"
    echo "Current: $PENDING"
    echo "Latest: $HEAD"
    exit 1
else
    echo "✓ Database is up to date"
    exit 0
fi
```

### Backup and Migrate

```bash
#!/bin/bash
# migrate_with_backup.sh

set -e

echo "Creating backup..."
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose -f docker-compose.prod.yml exec -T db \
    pg_dump -U postgres asset_tracker > backups/backup_$DATE.sql

echo "Backup created: backup_$DATE.sql"

echo "Applying migrations..."
docker-compose -f docker-compose.prod.yml exec web flask db upgrade

echo "Verifying migration..."
docker-compose -f docker-compose.prod.yml exec web flask db current

echo "✓ Migration complete"
```

## Additional Resources

- [Flask-Migrate Documentation](https://flask-migrate.readthedocs.io/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
