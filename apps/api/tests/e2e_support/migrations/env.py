"""E2E-only Alembic environment: never create or reconnect a database connection."""

from sqlalchemy import Connection

import sourcepilot.persistence.models  # noqa: F401
from alembic import context
from sourcepilot.persistence.base import Base

connection = context.config.attributes.get("connection")
if not isinstance(connection, Connection) or not connection.in_transaction():
    raise RuntimeError("E2E migrations require the validated connection and transaction.")

context.configure(connection=connection, target_metadata=Base.metadata)
with context.begin_transaction():
    context.run_migrations()
