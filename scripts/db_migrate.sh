#!/usr/bin/env bash
# Database Migration Helper Script
#
# Wrapper around Litestar/Alembic migration commands for easier usage.
#
# Usage:
#   ./scripts/db_migrate.sh create "migration description"  # Create new migration
#   ./scripts/db_migrate.sh up                               # Apply all pending migrations
#   ./scripts/db_migrate.sh down                             # Rollback one migration
#   ./scripts/db_migrate.sh status                           # Show migration status
#   ./scripts/db_migrate.sh history                          # Show migration history

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Get project directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"

# Change to backend directory
cd "$BACKEND_DIR"

# Function to show usage
show_usage() {
    echo "Usage: $0 <command> [args]"
    echo ""
    echo "Commands:"
    echo "  create <message>  Create a new migration"
    echo "  up                Apply all pending migrations"
    echo "  down              Rollback one migration"
    echo "  status            Show current migration status"
    echo "  history           Show migration history"
    echo ""
    echo "Examples:"
    echo "  $0 create 'Add email field to users'"
    echo "  $0 up"
    echo "  $0 down"
    echo "  $0 status"
}

# Check command
if [ $# -lt 1 ]; then
    show_usage
    exit 1
fi

COMMAND=$1

case "$COMMAND" in
    create|c|new)
        if [ $# -lt 2 ]; then
            echo -e "${RED}Error: Migration message required${NC}"
            echo "Usage: $0 create 'migration message'"
            exit 1
        fi
        
        MESSAGE="$2"
        echo -e "${BLUE}Creating new migration: $MESSAGE${NC}"
        uv run litestar database make-migrations -m "$MESSAGE"
        echo -e "${GREEN}✓ Migration created${NC}"
        echo ""
        echo "Next steps:"
        echo "  1. Review the generated migration in backend/app/db/migrations/versions/"
        echo "  2. Apply it: $0 up"
        ;;
        
    up|upgrade|apply)
        echo -e "${BLUE}Applying pending migrations...${NC}"
        uv run litestar database upgrade --no-prompt
        echo -e "${GREEN}✓ Migrations applied${NC}"
        ;;
        
    down|downgrade|rollback)
        echo -e "${YELLOW}Rolling back one migration...${NC}"
        read -p "Are you sure? (yes/no): " -r
        if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
            echo "Aborted."
            exit 0
        fi
        uv run litestar database downgrade --no-prompt
        echo -e "${GREEN}✓ Migration rolled back${NC}"
        ;;
        
    status|s)
        echo -e "${BLUE}Current migration status:${NC}"
        uv run litestar database show-current-revision
        ;;
        
    history|h|list)
        echo -e "${BLUE}Migration history:${NC}"
        uv run alembic history
        ;;
        
    *)
        echo -e "${RED}Unknown command: $COMMAND${NC}"
        echo ""
        show_usage
        exit 1
        ;;
esac
