#!/usr/bin/env bash
# Setup development database with migrations and legacy data

set -e

cd "$(dirname "$0")/.."

echo "🔄 Running database migrations..."
cd backend
export LITESTAR_APP="app.server.asgi:create_app"
uv run litestar database upgrade --no-prompt
cd ..

echo "📥 Loading legacy data from backup.sql..."
python3 scripts/migrate_legacy_data.py backup.sql

echo "✅ Database setup complete!"
echo ""
echo "Data loaded:"
docker compose exec -T postgres psql -U sessions -d sessions -c "
  SELECT 'sessions' as table_name, count(*) as row_count FROM sessions
  UNION ALL
  SELECT 'blocks', count(*) FROM blocks
  UNION ALL
  SELECT 'block_links', count(*) FROM block_links
  UNION ALL
  SELECT 'occurrences', count(*) FROM occurrences
  UNION ALL
  SELECT 'locations', count(*) FROM locations;
"
