#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# NEVEN TECH — One-Command Startup Script
# Usage: ./scripts/start.sh [mode]
#
# Modes:
#   dev       — Start in development mode with hot reload
#   demo      — Start with synthetic perception data
#   prod      — Start in production mode
#   docker    — Start with Docker Compose
# ─────────────────────────────────────────────────────────────────────────────

set -e

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

MODE=${1:-demo}

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║   ███╗   ██╗███████╗██╗   ██╗███████╗███╗   ██╗            ║"
echo "║   ████╗  ██║██╔════╝██║   ██║██╔════╝████╗  ██║            ║"
echo "║   ██╔██╗ ██║█████╗  ██║   ██║█████╗  ██╔██╗ ██║            ║"
echo "║   ██║╚██╗██║██╔══╝  ╚██╗ ██╔╝██╔══╝  ██║╚██╗██║            ║"
echo "║   ██║ ╚████║███████╗ ╚████╔╝ ███████╗██║ ╚████║            ║"
echo "║   ╚═╝  ╚═══╝╚══════╝  ╚═══╝  ╚══════╝╚═╝  ╚═══╝            ║"
echo "║                                                              ║"
echo "║   AI · SMART CITY SOLUTIONS                                  ║"
echo "║   The Physical World Runtime — v1.0.0                        ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${GREEN}Starting NEVEN in ${MODE} mode...${NC}"
echo ""

case $MODE in
    dev)
        echo "  Mode: Development (hot reload enabled)"
        echo "  URL:  http://localhost:8420"
        echo ""
        # Install in development mode
        pip install -e ".[dev]" --quiet 2>/dev/null || pip install -e . --quiet
        neven serve --reload --debug --port 8420
        ;;

    demo)
        echo "  Mode: Demo (synthetic perception data)"
        echo "  URL:  http://localhost:8420"
        echo ""
        # Install package
        pip install -e . --quiet 2>/dev/null || true
        python demo/run_demo.py --source synthetic --model builtin --port 8420
        ;;

    prod)
        echo "  Mode: Production"
        echo "  URL:  http://0.0.0.0:8420"
        echo ""
        # Load .env if exists
        if [ -f .env ]; then
            export $(cat .env | grep -v '^#' | xargs)
        fi
        pip install -e . --quiet 2>/dev/null || true
        neven serve --host 0.0.0.0 --port ${NEVEN_PORT:-8420} --workers ${NEVEN_WORKERS:-4}
        ;;

    docker)
        echo "  Mode: Docker Compose"
        echo "  URL:  http://localhost:8420"
        echo ""
        # Copy .env if not exists
        if [ ! -f .env ]; then
            cp .env.example .env
            echo -e "${YELLOW}  Created .env from .env.example${NC}"
        fi
        docker-compose up --build -d
        echo ""
        echo -e "${GREEN}  NEVEN is starting in Docker...${NC}"
        echo "  API:       http://localhost:8420"
        echo "  Dashboard: http://localhost:8420"
        echo "  Docs:      http://localhost:8420/docs"
        echo ""
        echo "  View logs: docker-compose logs -f neven-api"
        echo "  Stop:      docker-compose down"
        ;;

    *)
        echo "Unknown mode: $MODE"
        echo "Usage: ./scripts/start.sh [dev|demo|prod|docker]"
        exit 1
        ;;
esac
