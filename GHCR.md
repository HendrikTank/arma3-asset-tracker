# GitHub Container Registry (GHCR) Usage

## Overview

This repository automatically builds and publishes Docker images to GitHub Container Registry (ghcr.io) on every release.

**Image Name**: `ghcr.io/henriktank/arma3-asset-tracker`

---

## Automated Build

### How It Works

When you create a new release on GitHub:
1. GitHub Actions workflow triggers automatically
2. Docker image is built with production optimizations
3. Image is tagged with version numbers and `latest`
4. Image is pushed to ghcr.io

### Creating a Release

```bash
# Create a new release on GitHub
# 1. Go to: https://github.com/HendrikTank/arma3-asset-tracker/releases/new
# 2. Create a new tag (e.g., v1.0.0)
# 3. Add release notes
# 4. Click "Publish release"

# Or use GitHub CLI:
gh release create v1.0.0 --title "Release v1.0.0" --notes "Release notes here"
```

The workflow will automatically:
- Build the Docker image
- Tag it as: `v1.0.0`, `v1.0`, `v1`, `latest`
- Push to ghcr.io

---

## Using Published Images

### Pull the Image

```bash
# Pull latest version
docker pull ghcr.io/henriktank/arma3-asset-tracker:latest

# Pull specific version
docker pull ghcr.io/henriktank/arma3-asset-tracker:v1.0.0
docker pull ghcr.io/henriktank/arma3-asset-tracker:v1.0
docker pull ghcr.io/henriktank/arma3-asset-tracker:v1
```

### Authentication (for private repositories)

If the repository is private, authenticate first:

```bash
# Create a GitHub Personal Access Token with read:packages scope
# Then login:
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
```

### Update docker-compose.prod.yml

Instead of building locally, use the published image:

**Option 1: Use specific version (recommended for production)**

```yaml
services:
  web:
    image: ghcr.io/henriktank/arma3-asset-tracker:v1.0.0
    # Remove the 'build: .' line
    restart: unless-stopped
    environment:
      # ... rest of config
```

**Option 2: Use latest (for testing)**

```yaml
services:
  web:
    image: ghcr.io/henriktank/arma3-asset-tracker:latest
    restart: unless-stopped
    environment:
      # ... rest of config
```

### Deployment with GHCR Image

```bash
# Pull latest image
docker-compose -f docker-compose.prod.yml pull

# Start with pulled image (no build needed)
docker-compose -f docker-compose.prod.yml up -d

# Check running version
docker-compose -f docker-compose.prod.yml exec web python -c "print('Version info here')"
```

---

## Benefits of Using GHCR

✅ **No Build Time on Server** - Images are pre-built in CI
✅ **Faster Deployments** - Just pull and run
✅ **Consistent Builds** - Same image across all environments
✅ **Version Control** - Easy rollback to previous versions
✅ **Free for Public Repos** - Unlimited bandwidth and storage

---

## Workflow Configuration

### Workflow File Location
`.github/workflows/release.yml`

### Trigger Events
- **Release published** - Automatically on new release
- **Manual trigger** - Can be triggered manually from Actions tab

### Image Tags Generated

For release `v1.2.3`:
- `ghcr.io/henriktank/arma3-asset-tracker:v1.2.3` (exact version)
- `ghcr.io/henriktank/arma3-asset-tracker:v1.2` (minor version)
- `ghcr.io/henriktank/arma3-asset-tracker:v1` (major version)
- `ghcr.io/henriktank/arma3-asset-tracker:latest` (latest release)

---

## Manual Workflow Trigger

You can manually trigger the build without creating a release:

1. Go to: https://github.com/HendrikTank/arma3-asset-tracker/actions
2. Select "Build and Push Docker Image" workflow
3. Click "Run workflow"
4. Select branch and click "Run workflow"

---

## Rollback to Previous Version

```bash
# List available versions
docker images ghcr.io/henriktank/arma3-asset-tracker

# Update docker-compose.prod.yml to use previous version
# Change: image: ghcr.io/henriktank/arma3-asset-tracker:v1.1.0

# Deploy
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

---

## Monitoring Builds

### Check Build Status

1. Go to: https://github.com/HendrikTank/arma3-asset-tracker/actions
2. View workflow runs and logs
3. Check build artifacts and summaries

### Build Notifications

GitHub will notify you:
- ✅ When build succeeds
- ❌ When build fails
- 📧 Via email (if configured)

---

## Versioning Strategy

### Semantic Versioning

Use semantic versioning for releases:

- **Major** (v1.0.0 → v2.0.0): Breaking changes
- **Minor** (v1.0.0 → v1.1.0): New features, backward compatible
- **Patch** (v1.0.0 → v1.0.1): Bug fixes

### Creating Versions

```bash
# Bug fix release
gh release create v1.0.1 --title "Bug Fixes" --notes "Fixed login issue"

# New feature release
gh release create v1.1.0 --title "New Features" --notes "Added export functionality"

# Breaking changes release
gh release create v2.0.0 --title "Major Update" --notes "Updated authentication system"
```

---

## Advanced Usage

### Pull Specific Architecture

```bash
# For ARM64 (if multi-arch build is configured)
docker pull --platform linux/arm64 ghcr.io/henriktank/arma3-asset-tracker:latest

# For AMD64
docker pull --platform linux/amd64 ghcr.io/henriktank/arma3-asset-tracker:latest
```

### Inspect Image

```bash
# View image details
docker inspect ghcr.io/henriktank/arma3-asset-tracker:latest

# View image layers
docker history ghcr.io/henriktank/arma3-asset-tracker:latest
```

### Use in Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: arma3-tracker
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: web
        image: ghcr.io/henriktank/arma3-asset-tracker:v1.0.0
        imagePullPolicy: IfNotPresent
```

---

## Troubleshooting

### Image Not Found

**Problem**: `Error: manifest unknown`

**Solution**:
1. Check if release was published
2. Check workflow ran successfully
3. Verify image name is correct (lowercase)
4. For private repos, ensure you're authenticated

### Authentication Failed

**Problem**: `unauthorized: authentication required`

**Solution**:
```bash
# Login with personal access token
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Or create new token at:
# https://github.com/settings/tokens/new
# Scopes needed: read:packages
```

### Old Image Cached

**Problem**: Pulls old version even after new release

**Solution**:
```bash
# Force pull
docker-compose -f docker-compose.prod.yml pull --no-cache

# Or remove old image
docker rmi ghcr.io/henriktank/arma3-asset-tracker:latest
docker-compose -f docker-compose.prod.yml pull
```

---

## Security

### Image Scanning

Images are automatically scanned for vulnerabilities by GitHub.

View scan results:
1. Go to repository Security tab
2. View Dependabot alerts
3. Review vulnerability reports

### Keeping Images Updated

```bash
# Update base image and dependencies
# Edit Dockerfile and requirements.txt
# Create new release

gh release create v1.0.1 --title "Security Update" --notes "Updated dependencies"
```

---

## Cost and Limits

### GitHub Container Registry Limits

**Public Repositories (Free)**:
- ✅ Unlimited storage
- ✅ Unlimited bandwidth
- ✅ Unlimited downloads

**Private Repositories**:
- Storage: Included in GitHub plan
- Bandwidth: Included in GitHub plan
- Check: https://docs.github.com/en/billing/managing-billing-for-github-packages

---

## Related Documentation

- **Workflow File**: [.github/workflows/release.yml](.github/workflows/release.yml)
- **Dockerfile**: [Dockerfile](Dockerfile)
- **Production Compose**: [docker-compose.prod.yml](docker-compose.prod.yml)
- **Deployment Guide**: [DEPLOYMENT.md](DEPLOYMENT.md)

---

## Example: Complete Deployment with GHCR

```bash
# 1. Create release on GitHub (triggers build automatically)
gh release create v1.0.0 --title "Initial Release" --notes "First production release"

# 2. Wait for workflow to complete (check Actions tab)

# 3. On production server, update docker-compose.prod.yml
# Change from:
#   build: .
# To:
#   image: ghcr.io/henriktank/arma3-asset-tracker:v1.0.0

# 4. Deploy
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# 5. Verify
curl https://your-domain.com/health
```

---

## Summary

✅ **Automatic builds on release**  
✅ **Published to ghcr.io**  
✅ **Semantic versioning**  
✅ **Fast deployments (no build needed)**  
✅ **Easy rollbacks**  
✅ **Free for public repos**

**Next Steps**: Create your first release and the image will be automatically built and published!
