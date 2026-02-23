"""Demo BigQuery SQL Analytics for guest mode.

Provides synthetic responses for all BigQuery API endpoints so the Explorer
panel works without a real BigQuery connection.  The span data is sourced from
:class:`DemoDataGenerator` and flattened into ``_AllSpans``-compatible rows.
"""

from __future__ import annotations

import json
import re
from typing import Any

# ---------------------------------------------------------------------------
# Lazy singleton for the flattened rows (avoid re-generating on every call)
# ---------------------------------------------------------------------------
_CACHED_ROWS: list[dict[str, Any]] | None = None


def _get_all_rows() -> list[dict[str, Any]]:
    """Flatten all demo spans into _AllSpans-like rows.

    Returns a cached list of dicts, each matching the Cloud Trace BigQuery
    export schema columns.
    """
    global _CACHED_ROWS
    if _CACHED_ROWS is not None:
        return _CACHED_ROWS

    from sre_agent.tools.synthetic.demo_data_generator import DemoDataGenerator

    gen = DemoDataGenerator(seed=42)
    rows: list[dict[str, Any]] = []
    for trace in gen.get_all_traces():
        for span in trace["spans"]:
            rows.append(
                {
                    "span_id": span["span_id"],
                    "parent_span_id": span["parent_span_id"] or "",
                    "trace_id": span["trace_id"],
                    "name": span["name"],
                    "start_time": span["start_time"],
                    "end_time": span["end_time"],
                    "duration_nano": span["duration_nano"],
                    "status": span["status"],
                    "attributes": json.dumps(span["attributes"]),
                    "resource": json.dumps(span["resource"]),
                }
            )
    _CACHED_ROWS = rows
    return _CACHED_ROWS


# ---------------------------------------------------------------------------
# 1. Datasets
# ---------------------------------------------------------------------------


def get_demo_datasets() -> dict[str, list[str]]:
    """Return the list of demo BigQuery datasets."""
    return {"datasets": ["traces", "agentops"]}


# ---------------------------------------------------------------------------
# 2. Tables
# ---------------------------------------------------------------------------

_DATASET_TABLES: dict[str, list[str]] = {
    "traces": ["_AllSpans", "_AllLogs"],
    "agentops": [
        "agent_spans_raw",
        "agent_topology_nodes",
        "agent_topology_edges",
        "agent_trajectories",
        "agent_graph_hourly",
    ],
}


def get_demo_tables(dataset_id: str) -> dict[str, list[str]]:
    """Return tables for the given demo dataset."""
    return {"tables": _DATASET_TABLES.get(dataset_id, [])}


# ---------------------------------------------------------------------------
# 3. Table schemas
# ---------------------------------------------------------------------------

_ALLSPANS_SCHEMA: list[dict[str, Any]] = [
    {"name": "span_id", "type": "STRING", "mode": "NULLABLE"},
    {"name": "parent_span_id", "type": "STRING", "mode": "NULLABLE"},
    {"name": "trace_id", "type": "STRING", "mode": "NULLABLE"},
    {"name": "name", "type": "STRING", "mode": "NULLABLE"},
    {"name": "start_time", "type": "TIMESTAMP", "mode": "NULLABLE"},
    {"name": "end_time", "type": "TIMESTAMP", "mode": "NULLABLE"},
    {"name": "duration_nano", "type": "INT64", "mode": "NULLABLE"},
    {
        "name": "status",
        "type": "RECORD",
        "mode": "NULLABLE",
        "fields": [
            {"name": "code", "type": "INT64", "mode": "NULLABLE"},
            {"name": "message", "type": "STRING", "mode": "NULLABLE"},
        ],
    },
    {"name": "attributes", "type": "JSON", "mode": "NULLABLE"},
    {
        "name": "resource",
        "type": "RECORD",
        "mode": "NULLABLE",
        "fields": [
            {"name": "attributes", "type": "JSON", "mode": "NULLABLE"},
        ],
    },
]

_ALLLOGS_SCHEMA: list[dict[str, Any]] = [
    {"name": "timestamp", "type": "TIMESTAMP", "mode": "NULLABLE"},
    {"name": "severity", "type": "STRING", "mode": "NULLABLE"},
    {"name": "log_name", "type": "STRING", "mode": "NULLABLE"},
    {"name": "text_payload", "type": "STRING", "mode": "NULLABLE"},
    {"name": "json_payload", "type": "JSON", "mode": "NULLABLE"},
    {"name": "trace_id", "type": "STRING", "mode": "NULLABLE"},
    {"name": "span_id", "type": "STRING", "mode": "NULLABLE"},
    {"name": "resource", "type": "JSON", "mode": "NULLABLE"},
]

_AGENTOPS_SIMPLE_SCHEMA: list[dict[str, Any]] = [
    {"name": "id", "type": "STRING", "mode": "NULLABLE"},
    {"name": "timestamp", "type": "TIMESTAMP", "mode": "NULLABLE"},
    {"name": "agent_name", "type": "STRING", "mode": "NULLABLE"},
    {"name": "service_name", "type": "STRING", "mode": "NULLABLE"},
    {"name": "value", "type": "FLOAT64", "mode": "NULLABLE"},
]

_TABLE_SCHEMAS: dict[str, list[dict[str, Any]]] = {
    "traces._AllSpans": _ALLSPANS_SCHEMA,
    "traces._AllLogs": _ALLLOGS_SCHEMA,
}


def get_demo_table_schema(
    dataset_id: str, table_id: str
) -> dict[str, list[dict[str, Any]]]:
    """Return the schema for the given demo table."""
    key = f"{dataset_id}.{table_id}"
    schema = _TABLE_SCHEMAS.get(key, _AGENTOPS_SIMPLE_SCHEMA)
    return {"schema": schema}


# ---------------------------------------------------------------------------
# 4. JSON keys
# ---------------------------------------------------------------------------

_JSON_KEYS: dict[str, list[str]] = {
    "traces._AllSpans.attributes": [
        "gen_ai.operation.name",
        "gen_ai.agent.name",
        "gen_ai.tool.name",
        "gen_ai.usage.input_tokens",
        "gen_ai.usage.output_tokens",
        "gen_ai.request.model",
        "gen_ai.response.model",
        "gen_ai.conversation.id",
        "gen_ai.system",
    ],
    "traces._AllSpans.resource": [
        "service.name",
        "service.version",
        "cloud.provider",
        "cloud.region",
        "cloud.platform",
        "cloud.resource_id",
    ],
}


def get_demo_json_keys(
    dataset_id: str, table_id: str, column_name: str
) -> dict[str, list[str]]:
    """Return inferred JSON keys for a demo column."""
    key = f"{dataset_id}.{table_id}.{column_name}"
    return {"keys": _JSON_KEYS.get(key, [])}


# ---------------------------------------------------------------------------
# 5. SQL query executor
# ---------------------------------------------------------------------------

# Regex patterns for simple SQL parsing
_RE_SELECT = re.compile(
    r"^\s*SELECT\s+(.+?)\s+FROM\s+",
    re.IGNORECASE | re.DOTALL,
)
_RE_FROM = re.compile(
    r"\bFROM\s+([\w.`]+)",
    re.IGNORECASE,
)
_RE_WHERE = re.compile(
    r"\bWHERE\s+(.+?)(?:\s+GROUP\s+BY|\s+ORDER\s+BY|\s+LIMIT|\s*$)",
    re.IGNORECASE | re.DOTALL,
)
_RE_GROUP_BY = re.compile(
    r"\bGROUP\s+BY\s+(.+?)(?:\s+ORDER\s+BY|\s+LIMIT|\s*$)",
    re.IGNORECASE | re.DOTALL,
)
_RE_ORDER_BY = re.compile(
    r"\bORDER\s+BY\s+(.+?)(?:\s+LIMIT|\s*$)",
    re.IGNORECASE | re.DOTALL,
)
_RE_LIMIT = re.compile(
    r"\bLIMIT\s+(\d+)",
    re.IGNORECASE,
)


def _parse_select_columns(select_clause: str) -> list[str]:
    """Parse the SELECT column list into individual column expressions."""
    cols: list[str] = []
    depth = 0
    current = ""
    for ch in select_clause:
        if ch == "(":
            depth += 1
            current += ch
        elif ch == ")":
            depth -= 1
            current += ch
        elif ch == "," and depth == 0:
            cols.append(current.strip())
            current = ""
        else:
            current += ch
    if current.strip():
        cols.append(current.strip())
    return cols


def _resolve_alias(expr: str) -> tuple[str, str]:
    """Split ``expr AS alias`` into (expr, alias).  Returns (expr, expr) if no alias."""
    m = re.match(r"(.+?)\s+(?:AS\s+)?(\w+)\s*$", expr, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return expr.strip(), expr.strip()


def _evaluate_where(row: dict[str, Any], where_clause: str) -> bool:
    """Evaluate a simple WHERE clause against a single row.

    Supports:
      - column = 'value'
      - column LIKE '%pattern%'
      - column = number
      - AND-joined conditions
    """
    # Split on AND (top-level only)
    conditions = re.split(r"\s+AND\s+", where_clause, flags=re.IGNORECASE)
    for cond in conditions:
        cond = cond.strip()
        if not cond:
            continue

        # LIKE
        m = re.match(r"(\w+)\s+LIKE\s+'(.*?)'", cond, re.IGNORECASE)
        if m:
            col, pattern = m.group(1), m.group(2)
            val = str(row.get(col, ""))
            regex = re.escape(pattern).replace(r"\%", ".*")
            if not re.fullmatch(regex, val, re.IGNORECASE):
                return False
            continue

        # Equality
        m = re.match(r"(\w+)\s*=\s*'(.*?)'", cond)
        if m:
            col, expected = m.group(1), m.group(2)
            if str(row.get(col, "")) != expected:
                return False
            continue

        m = re.match(r"(\w+)\s*=\s*(\d+)", cond)
        if m:
            col, expected_int = m.group(1), int(m.group(2))
            if row.get(col) != expected_int:
                return False
            continue

        # Not-equal
        m = re.match(r"(\w+)\s*!=\s*'(.*?)'", cond)
        if m:
            col, expected = m.group(1), m.group(2)
            if str(row.get(col, "")) == expected:
                return False
            continue

    return True


def _extract_agg(expr: str) -> tuple[str, str | None]:
    """Detect aggregate function.  Returns (func_upper, inner_col) or ('', None)."""
    m = re.match(r"(COUNT|SUM|AVG|MIN|MAX)\s*\(\s*(.+?)\s*\)", expr, re.IGNORECASE)
    if m:
        return m.group(1).upper(), m.group(2)
    return "", None


def _compute_agg(func: str, col: str | None, rows: list[dict[str, Any]]) -> int | float:
    """Compute an aggregate value over *rows*."""
    if func == "COUNT":
        if col == "*" or col is None:
            return len(rows)
        col_str: str = col
        return sum(1 for r in rows if r.get(col_str) is not None)

    if not col:
        return 0
    col_name: str = col
    values = [
        float(r[col_name]) for r in rows if col_name in r and r[col_name] is not None
    ]
    if not values:
        return 0
    if func == "SUM":
        return sum(values)
    if func == "AVG":
        return round(sum(values) / len(values), 2)
    if func == "MIN":
        return min(values)
    if func == "MAX":
        return max(values)
    return 0


def execute_demo_query(sql: str) -> dict[str, Any]:
    """Execute a simplified SQL query over the demo span data.

    Supports basic SELECT, WHERE (=, LIKE, AND), GROUP BY with
    aggregates (COUNT, SUM, AVG, MIN, MAX), ORDER BY, LIMIT, and
    SELECT DISTINCT.

    For any query that cannot be parsed, the first 100 rows are returned
    as a fallback.
    """
    rows = _get_all_rows()

    try:
        return _execute_parsed_query(sql, rows)
    except Exception:
        # Fallback: return the first 100 rows
        if not rows:
            return {"columns": [], "rows": []}
        columns = list(rows[0].keys())
        return {"columns": columns, "rows": rows[:100]}


def _execute_parsed_query(sql: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Internal: parse and execute *sql* against *rows*."""
    # --- SELECT columns ---
    sel_match = _RE_SELECT.search(sql)
    if not sel_match:
        raise ValueError("Cannot parse SELECT clause")
    select_raw = sel_match.group(1).strip()

    is_distinct = False
    if select_raw.upper().startswith("DISTINCT"):
        is_distinct = True
        select_raw = select_raw[len("DISTINCT") :].strip()

    col_exprs = _parse_select_columns(select_raw)

    # --- WHERE ---
    where_match = _RE_WHERE.search(sql)
    if where_match:
        where_clause = where_match.group(1).strip()
        rows = [r for r in rows if _evaluate_where(r, where_clause)]

    # --- GROUP BY ---
    group_match = _RE_GROUP_BY.search(sql)
    if group_match:
        group_cols = [c.strip() for c in group_match.group(1).split(",")]
        return _execute_group_by(col_exprs, group_cols, rows, sql)

    # --- Check for bare aggregates (no GROUP BY) ---
    has_agg = any(_extract_agg(e.split(" AS ")[0].strip())[0] for e in col_exprs)
    if has_agg and not group_match:
        return _execute_group_by(col_exprs, [], rows, sql)

    # --- Simple SELECT (with optional DISTINCT) ---
    resolved = [_resolve_alias(e) for e in col_exprs]
    out_columns = [alias for _, alias in resolved]
    is_star = len(resolved) == 1 and resolved[0][0] == "*"

    if is_star:
        out_columns = list(rows[0].keys()) if rows else []
        result_rows = [dict(r) for r in rows]
    else:
        result_rows = []
        for r in rows:
            out: dict[str, Any] = {}
            for expr, alias in resolved:
                out[alias] = r.get(expr, None)
            result_rows.append(out)

    if is_distinct:
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for r in result_rows:
            key = json.dumps(r, sort_keys=True, default=str)
            if key not in seen:
                seen.add(key)
                unique.append(r)
        result_rows = unique

    # --- ORDER BY ---
    order_match = _RE_ORDER_BY.search(sql)
    if order_match:
        order_clause = order_match.group(1).strip()
        parts = order_clause.split(",")
        for part in reversed(parts):
            part = part.strip()
            desc = part.upper().endswith(" DESC")
            col_name = re.sub(
                r"\s+(ASC|DESC)\s*$", "", part, flags=re.IGNORECASE
            ).strip()
            result_rows.sort(
                key=lambda r, c=col_name: (r.get(c) is None, r.get(c)),  # type: ignore[misc]
                reverse=desc,
            )

    # --- LIMIT ---
    limit_match = _RE_LIMIT.search(sql)
    limit = int(limit_match.group(1)) if limit_match else 100
    result_rows = result_rows[:limit]

    return {"columns": out_columns, "rows": result_rows}


def _execute_group_by(
    col_exprs: list[str],
    group_cols: list[str],
    rows: list[dict[str, Any]],
    sql: str,
) -> dict[str, Any]:
    """Handle GROUP BY (or bare aggregate) queries."""
    # Build groups
    groups: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        key = json.dumps([r.get(gc) for gc in group_cols], default=str)
        groups.setdefault(key, []).append(r)

    resolved = [_resolve_alias(e) for e in col_exprs]
    out_columns = [alias for _, alias in resolved]

    result_rows: list[dict[str, Any]] = []
    for key, group_rows in groups.items():
        out: dict[str, Any] = {}
        group_vals = json.loads(key)
        for idx, gc in enumerate(group_cols):
            out[gc] = group_vals[idx]

        for expr, alias in resolved:
            func, inner = _extract_agg(expr)
            if func:
                out[alias] = _compute_agg(func, inner, group_rows)
            elif alias not in out:
                out[alias] = group_rows[0].get(expr) if group_rows else None
        result_rows.append(out)

    # --- ORDER BY ---
    order_match = _RE_ORDER_BY.search(sql)
    if order_match:
        order_clause = order_match.group(1).strip()
        parts = order_clause.split(",")
        for part in reversed(parts):
            part = part.strip()
            desc = part.upper().endswith(" DESC")
            col_name = re.sub(
                r"\s+(ASC|DESC)\s*$", "", part, flags=re.IGNORECASE
            ).strip()
            result_rows.sort(
                key=lambda r, c=col_name: (r.get(c) is None, r.get(c)),  # type: ignore[misc]
                reverse=desc,
            )

    # --- LIMIT ---
    limit_match = _RE_LIMIT.search(sql)
    limit = int(limit_match.group(1)) if limit_match else 100
    result_rows = result_rows[:limit]

    return {"columns": out_columns, "rows": result_rows}
