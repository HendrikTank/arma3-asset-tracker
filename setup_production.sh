#!/bin/bash
# Production Deployment Setup Script
# This script helps set up the production environment

set -e

echo "================================================"
echo "ARMA3 Asset Tracker - Production Setup"
echo "================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env exists
if [ -f .env ]; then
    echo -e "${YELLOW}Warning: .env file already exists!${NC}"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Keeping existing .env file"
        ENV_EXISTS=true
    fi
fi

if [ -z "$ENV_EXISTS" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    
    # Generate secure secret key
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    
    # Update secret key in .env
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/your-secret-key-here-change-me/$SECRET_KEY/" .env
    else
        # Linux
        sed -i "s/your-secret-key-here-change-me/$SECRET_KEY/" .env
    fi
    
    echo -e "${GREEN}✓ .env file created with secure secret key${NC}"
fi

echo ""
echo "================================================"
echo "Configuration Steps"
echo "================================================"
echo ""
echo "Please complete the following configuration:"
echo ""
echo "1. Edit .env file and update:"
echo "   - POSTGRES_PASSWORD (line 33)"
echo "   - DATABASE_URL with your PostgreSQL password"
echo "   - Your domain name (if known)"
echo ""
echo "2. Edit docker-compose.prod.yml and update:"
echo "   - Line 36: Replace 'your-domain.com' with your actual domain"
echo ""
echo "3. Ensure Traefik is running:"
echo "   - Create network: docker network create traefik_network"
echo ""

read -p "Press Enter when you've completed these steps..."

echo ""
echo "================================================"
echo "Deployment"
echo "================================================"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}✗ Docker is not running${NC}"
    echo "Please start Docker and run this script again"
    exit 1
fi

echo -e "${GREEN}✓ Docker is running${NC}"

# Check if traefik network exists
if ! docker network inspect traefik_network > /dev/null 2>&1; then
    echo -e "${YELLOW}Warning: traefik_network does not exist${NC}"
    read -p "Create traefik_network now? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        docker network create traefik_network
        echo -e "${GREEN}✓ Created traefik_network${NC}"
    else
        echo -e "${YELLOW}⚠ You must create traefik_network before deployment${NC}"
    fi
fi

echo ""
read -p "Build and start containers? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Building containers..."
    docker-compose -f docker-compose.prod.yml build
    
    echo ""
    echo "Starting containers..."
    docker-compose -f docker-compose.prod.yml up -d
    
    echo ""
    echo "Waiting for services to be healthy..."
    sleep 10
    
    # Check container status
    docker-compose -f docker-compose.prod.yml ps
    
    echo ""
    echo -e "${GREEN}✓ Containers started${NC}"
    
    echo ""
    echo "================================================"
    echo "Database Setup"
    echo "================================================"
    echo ""
    
    read -p "Initialize database migrations? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        echo "Initializing Flask-Migrate..."
        docker-compose -f docker-compose.prod.yml exec -T web flask db init || echo "Migrations already initialized"
        
        echo "Creating initial migration..."
        docker-compose -f docker-compose.prod.yml exec -T web flask db migrate -m "Initial migration"
        
        echo "Applying migration..."
        docker-compose -f docker-compose.prod.yml exec -T web flask db upgrade
        
        echo -e "${GREEN}✓ Database migrations complete${NC}"
    fi
    
    echo ""
    read -p "Create admin user? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        docker-compose -f docker-compose.prod.yml exec web python create_admin.py
    fi
    
    echo ""
    echo "================================================"
    echo "Deployment Complete!"
    echo "================================================"
    echo ""
    echo "Your application should now be running at:"
    echo "  https://your-domain.com"
    echo ""
    echo "Health check endpoints:"
    echo "  https://your-domain.com/health"
    echo "  https://your-domain.com/ready"
    echo ""
    echo "To view logs:"
    echo "  docker-compose -f docker-compose.prod.yml logs -f"
    echo ""
    echo "For troubleshooting, see:"
    echo "  - README.md"
    echo "  - DEPLOYMENT.md"
    echo "  - MIGRATIONS.md"
    echo ""
else
    echo ""
    echo "Deployment cancelled. To deploy manually:"
    echo "  docker-compose -f docker-compose.prod.yml up -d --build"
    echo ""
    echo "See DEPLOYMENT.md for detailed instructions"
fi

echo ""
echo -e "${GREEN}Setup script complete!${NC}"
