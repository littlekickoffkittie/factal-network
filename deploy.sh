#!/bin/bash
# FractalChain Production Deployment Script
#
# This script provides automated deployment and management for FractalChain nodes
# Usage: ./deploy.sh [command] [options]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="fractalchain"
DOCKER_IMAGE="fractalchain:latest"
DATA_DIR="$HOME/.fractalchain"
LOG_DIR="$DATA_DIR/logs"
BACKUP_DIR="$DATA_DIR/backups"

# Functions
print_header() {
    echo -e "${BLUE}==========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}==========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"

    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    print_success "Docker found: $(docker --version)"

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_warning "Docker Compose not found, using 'docker compose' instead"
    else
        print_success "Docker Compose found: $(docker-compose --version)"
    fi

    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_warning "Python 3 not found (required for native deployment)"
    else
        print_success "Python 3 found: $(python3 --version)"
    fi

    echo ""
}

# Build Docker image
build_docker() {
    print_header "Building Docker Image"

    docker build -t $DOCKER_IMAGE .
    print_success "Docker image built successfully"

    echo ""
}

# Deploy with Docker
deploy_docker() {
    print_header "Deploying FractalChain with Docker"

    # Create necessary directories
    mkdir -p "$DATA_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "$BACKUP_DIR"
    print_success "Created data directories"

    # Build image
    build_docker

    # Stop existing container
    if docker ps -a | grep -q "$PROJECT_NAME"; then
        print_info "Stopping existing container..."
        docker stop "$PROJECT_NAME" 2>/dev/null || true
        docker rm "$PROJECT_NAME" 2>/dev/null || true
    fi

    # Run container
    print_info "Starting FractalChain container..."
    docker run -d \
        --name "$PROJECT_NAME" \
        --restart unless-stopped \
        -p 8333:8333 \
        -p 8545:8545 \
        -p 8080:8080 \
        -v "$DATA_DIR:/home/fractalchain/.fractalchain" \
        $DOCKER_IMAGE

    print_success "FractalChain deployed successfully!"
    print_info "P2P Port: 8333"
    print_info "RPC API: http://localhost:8545"
    print_info "Web Explorer: http://localhost:8080"

    echo ""
}

# Deploy with Docker Compose
deploy_compose() {
    print_header "Deploying with Docker Compose"

    # Create directories
    mkdir -p "$DATA_DIR"
    mkdir -p "$LOG_DIR"

    # Start services
    if command -v docker-compose &> /dev/null; then
        docker-compose up -d --build
    else
        docker compose up -d --build
    fi

    print_success "Services started with Docker Compose"
    echo ""
}

# Native deployment
deploy_native() {
    print_header "Native Deployment"

    # Create virtual environment
    if [ ! -d "venv" ]; then
        print_info "Creating virtual environment..."
        python3 -m venv venv
        print_success "Virtual environment created"
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Install dependencies
    print_info "Installing dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    print_success "Dependencies installed"

    # Create directories
    mkdir -p "$DATA_DIR"
    mkdir -p "$LOG_DIR"

    print_success "Native deployment ready!"
    print_info "Activate virtual environment: source venv/bin/activate"
    print_info "Start node: python3 main.py"

    echo ""
}

# Start node
start_node() {
    print_header "Starting FractalChain Node"

    if docker ps | grep -q "$PROJECT_NAME"; then
        print_warning "Container already running"
    elif docker ps -a | grep -q "$PROJECT_NAME"; then
        docker start "$PROJECT_NAME"
        print_success "Container started"
    else
        print_error "No deployed container found. Run './deploy.sh docker' first"
        exit 1
    fi

    echo ""
}

# Stop node
stop_node() {
    print_header "Stopping FractalChain Node"

    if docker ps | grep -q "$PROJECT_NAME"; then
        docker stop "$PROJECT_NAME"
        print_success "Container stopped"
    else
        print_warning "Container not running"
    fi

    echo ""
}

# View logs
view_logs() {
    print_header "FractalChain Logs"

    if docker ps | grep -q "$PROJECT_NAME"; then
        docker logs -f "$PROJECT_NAME"
    else
        print_error "Container not running"
        exit 1
    fi
}

# Check status
check_status() {
    print_header "FractalChain Status"

    if docker ps | grep -q "$PROJECT_NAME"; then
        print_success "Node is running"
        echo ""
        docker ps | grep "$PROJECT_NAME"
        echo ""

        # Check RPC API
        if command -v curl &> /dev/null; then
            print_info "Checking RPC API..."
            if curl -s http://localhost:8545 > /dev/null 2>&1; then
                print_success "RPC API is responsive"
            else
                print_warning "RPC API not responding"
            fi
        fi
    else
        print_warning "Node is not running"
    fi

    echo ""
}

# Backup blockchain data
backup_data() {
    print_header "Backing Up Blockchain Data"

    BACKUP_FILE="$BACKUP_DIR/fractalchain_backup_$(date +%Y%m%d_%H%M%S).tar.gz"

    print_info "Creating backup..."
    tar -czf "$BACKUP_FILE" -C "$DATA_DIR" mainnet
    print_success "Backup created: $BACKUP_FILE"

    # Keep only last 5 backups
    print_info "Cleaning old backups..."
    ls -t "$BACKUP_DIR"/fractalchain_backup_*.tar.gz | tail -n +6 | xargs -r rm
    print_success "Backup cleanup complete"

    echo ""
}

# Update node
update_node() {
    print_header "Updating FractalChain"

    # Pull latest code
    if [ -d ".git" ]; then
        print_info "Pulling latest changes..."
        git pull
        print_success "Code updated"
    fi

    # Rebuild and restart
    print_info "Rebuilding..."
    build_docker

    print_info "Restarting node..."
    stop_node
    start_node

    print_success "Update complete!"
    echo ""
}

# Show usage
usage() {
    echo "FractalChain Deployment Script"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  docker          Deploy using Docker"
    echo "  compose         Deploy using Docker Compose"
    echo "  native          Setup native Python deployment"
    echo "  start           Start the node"
    echo "  stop            Stop the node"
    echo "  restart         Restart the node"
    echo "  status          Check node status"
    echo "  logs            View node logs"
    echo "  backup          Backup blockchain data"
    echo "  update          Update and restart node"
    echo "  clean           Remove all containers and data"
    echo "  help            Show this help message"
    echo ""
}

# Clean deployment
clean_deployment() {
    print_header "Cleaning Deployment"

    print_warning "This will remove all containers and data!"
    read -p "Are you sure? (yes/no): " -r
    echo

    if [[ $REPLY == "yes" ]]; then
        docker stop "$PROJECT_NAME" 2>/dev/null || true
        docker rm "$PROJECT_NAME" 2>/dev/null || true
        docker rmi "$DOCKER_IMAGE" 2>/dev/null || true
        print_success "Cleanup complete"
    else
        print_info "Cleanup cancelled"
    fi

    echo ""
}

# Main script
main() {
    case "${1:-help}" in
        docker)
            check_prerequisites
            deploy_docker
            ;;
        compose)
            check_prerequisites
            deploy_compose
            ;;
        native)
            check_prerequisites
            deploy_native
            ;;
        start)
            start_node
            ;;
        stop)
            stop_node
            ;;
        restart)
            stop_node
            start_node
            ;;
        status)
            check_status
            ;;
        logs)
            view_logs
            ;;
        backup)
            backup_data
            ;;
        update)
            update_node
            ;;
        clean)
            clean_deployment
            ;;
        help|--help|-h)
            usage
            ;;
        *)
            print_error "Unknown command: $1"
            echo ""
            usage
            exit 1
            ;;
    esac
}

# Run main
main "$@"
