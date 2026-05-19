# Alembic migrations

```bash
# Create new migration (auto-detect changes from models)
uv run alembic revision --autogenerate -m "describe change"

# Apply migrations
uv run alembic upgrade head

# Roll back one
uv run alembic downgrade -1
```

`0001_initial.py` is hand-written because it needs to:
1. Create `matches` and `participants` as partitioned tables
2. Add GIN indexes on array columns (which Alembic autogenerate doesn't handle well)
3. Create initial monthly partitions

After that, autogenerate works fine for normal column/table changes.
