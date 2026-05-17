from typing import Any
from sqlalchemy import Table, select, insert, update, delete, Select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.utils import row_to_dict, rows_to_list


def _apply_filters(stmt: Select, table: Table, filters: dict[str, Any]) -> Select:
    """Apply multiple field filters to a statement"""
    for field_name, field_value in filters.items():
        if not hasattr(table.c, field_name):
            raise ValueError(f"Table {table.name} does not have field {field_name}")
        stmt = stmt.where(getattr(table.c, field_name) == field_value)
    return stmt


async def get_by_id(session: AsyncSession, table: Table, record_id: int) -> dict | None:
    """Get a single record by ID"""
    stmt = select(table).where(table.c.id == record_id)
    result = await session.execute(stmt)
    return row_to_dict(result)


async def get_by_field(
    session: AsyncSession,
    table: Table,
    field_name: str,
    field_value: Any,
) -> dict | None:
    """Get a single record by any field"""
    if not hasattr(table.c, field_name):
        raise ValueError(f"Table {table.name} does not have field {field_name}")

    stmt = select(table).where(getattr(table.c, field_name) == field_value)
    result = await session.execute(stmt)
    return row_to_dict(result)


async def get_by_fields(
    session: AsyncSession,
    table: Table,
    **filters: Any,
) -> dict | None:
    """Get a single record by multiple fields"""
    stmt = _apply_filters(select(table), table, filters)
    result = await session.execute(stmt)
    return row_to_dict(result)


async def get_all(
    session: AsyncSession,
    table: Table,
    order_by: str | None = None,
    **filters: Any,
) -> list[dict]:
    """Get all records with optional filters and ordering"""
    stmt = _apply_filters(select(table), table, filters)

    if order_by and hasattr(table.c, order_by):
        stmt = stmt.order_by(getattr(table.c, order_by))

    result = await session.execute(stmt)
    return rows_to_list(result)


async def create(
    session: AsyncSession,
    table: Table,
    **values: Any,
) -> dict:
    """Create a new record"""
    stmt = insert(table).values(**values).returning(table)
    result = await session.execute(stmt)
    await session.commit()
    return row_to_dict(result)


async def update_by_id(
    session: AsyncSession,
    table: Table,
    record_id: int,
    **values: Any,
) -> dict | None:
    """Update a record by ID"""
    stmt = (
        update(table)
        .where(table.c.id == record_id)
        .values(**values)
        .returning(table)
    )
    result = await session.execute(stmt)
    await session.commit()
    return row_to_dict(result)


async def update_by_fields(
    session: AsyncSession,
    table: Table,
    filters: dict[str, Any],
    values: dict[str, Any],
) -> dict | None:
    """Update a record by multiple fields"""
    stmt = update(table)
    for field_name, field_value in filters.items():
        if not hasattr(table.c, field_name):
            raise ValueError(f"Table {table.name} does not have field {field_name}")
        stmt = stmt.where(getattr(table.c, field_name) == field_value)

    stmt = stmt.values(**values).returning(table)
    result = await session.execute(stmt)
    await session.commit()
    return row_to_dict(result)


async def delete_by_id(session: AsyncSession, table: Table, record_id: int) -> bool:
    """Delete a record by ID"""
    stmt = delete(table).where(table.c.id == record_id)
    await session.execute(stmt)
    await session.commit()
    return True


async def delete_by_fields(
    session: AsyncSession,
    table: Table,
    **filters: Any,
) -> bool:
    """Delete records by multiple fields"""
    stmt = delete(table)
    for field_name, field_value in filters.items():
        if not hasattr(table.c, field_name):
            raise ValueError(f"Table {table.name} does not have field {field_name}")
        stmt = stmt.where(getattr(table.c, field_name) == field_value)

    await session.execute(stmt)
    await session.commit()
    return True


async def exists(
    session: AsyncSession,
    table: Table,
    **filters: Any,
) -> bool:
    """Check if a record exists with given filters"""
    stmt = _apply_filters(select(table), table, filters).limit(1)
    result = await session.execute(stmt)
    return result.first() is not None

