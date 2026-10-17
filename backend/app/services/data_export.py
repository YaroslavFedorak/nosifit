"""Everything stored about one user, as JSON (right of access / portability).

Rows of every table with a foreign key to users.id are included, plus the
child tables listed in CHILD_TABLES, reached only through the user's own
parent rows, and the rows users.* points to (LINKED_FROM_USER), so no other
user's row can appear. New tables that reference
users are picked up automatically. Secrets are left out (EXCLUDED_COLUMNS).
"""

from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import select

from backend.app.extensions import db

# child table -> (its foreign-key column, the parent table that column points to)
CHILD_TABLES = {
    "meal_items": ("meal_id", "meals"),
    "nutrition_dish_items": ("dish_id", "nutrition_dishes"),
    "nutrition_product_names": ("product_id", "nutrition_products"),
    "session_exercises": ("session_id", "training_sessions"),
}
# table -> the users column that points to its row (the link goes the other way)
LINKED_FROM_USER = {"te_fatigue_state": "fatigue_state_id"}
EXCLUDED_COLUMNS = {"users": {"password"}}


def _json(value):
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _rows(table, where):
    hidden = EXCLUDED_COLUMNS.get(table.name, set())
    result = db.session.execute(select(table).where(where).order_by(*table.primary_key.columns))
    return [
        {key: _json(value) for key, value in row._mapping.items() if key not in hidden}
        for row in result
    ]


def export_user_data(user) -> dict:
    tables = db.metadata.tables
    users = tables["users"]
    data = {"users": _rows(users, users.c.id == user.id)}

    for table in sorted(tables.values(), key=lambda t: t.name):
        user_columns = [
            column
            for column in table.columns
            for fk in column.foreign_keys
            if fk.column.table.name == "users" and fk.column.name == "id"
        ]
        if table.name == "users" or not user_columns:
            continue
        condition = user_columns[0] == user.id
        for column in user_columns[1:]:
            condition = condition | (column == user.id)
        data[table.name] = _rows(table, condition)

    for table_name, column_name in LINKED_FROM_USER.items():
        table = tables[table_name]
        linked_id = getattr(user, column_name, None)
        data[table_name] = _rows(table, table.c.id == linked_id) if linked_id is not None else []

    for child_name, (fk_name, parent_name) in CHILD_TABLES.items():
        child, parent = tables[child_name], tables[parent_name]
        parent_ids = [row["id"] for row in data.get(parent_name, [])]
        data[child_name] = _rows(child, child.c[fk_name].in_(parent_ids)) if parent_ids else []

    return {
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "user_id": user.id,
        "tables": data,
    }
