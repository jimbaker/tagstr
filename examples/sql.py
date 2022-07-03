from __future__ import annotations

import re
import sqlite3
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from taglib import Thunk


# NOTE: other dialects have different rules, for example Postgres
# allows for Unicode in the unquoted identifier, per the docs.
SQLITE3_VALID_UNQUOTED_IDENTIFIER_RE = re.compile(r'[a-z_][a-z0-9_]*')


def _quote_identifier(name: str) -> str:
    if not name:
        raise ValueError("Identifiers cannot be an empty string")
    elif SQLITE3_VALID_UNQUOTED_IDENTIFIER_RE.fullmatch(name):
        # Do not quote if possible
        return name
    else:
        s = name.replace('"', '""')  # double any quoting to escape it
        return f'"{s}"'


class Identifier(str):
    def __new__(cls, name):
        return super().__new__(cls, _quote_identifier(name))


@dataclass
class Param:
    raw: str
    value: Any


@dataclass
class SQL(Sequence):
    """Builds a SQL statements and any bindings from a list of its parts"""
    parts: list[str | Param | SQL]
    sql: str = field(init=False)
    bindings: dict[str, Any] = field(init=False)

    def __post_init__(self):
        self.sql, self.bindings = analyze_sql(self.parts)

    def __getitem__(self, index):
        match index:
            case 0: return self.sql 
            case 1: return self.bindings
            case _: raise IndexError
    
    def __len__(self):
        return 2

    def to_sqlalchemy(self):
        # See https://docs.sqlalchemy.org/en/14/core/sqlelement.html
        # this allows interoperation with SQLAlchemy
        from sqlalchemy import text
        return text(self.sql).bindparams(**self.bindings)


def analyze_sql(parts, bindings=None, param_counts=None) -> tuple[str, dict[str, Any]]:
    """Analyzes the SQL statement with respect to its parts, ensuring unique param names"""
    if bindings is None:
        bindings = {}        
    if param_counts is None:
        param_counts = defaultdict(int)

    text = []
    for part in parts:
        match part:
            case str():
                text.append(part)
            case Identifier(value):
                text.append(value)
            case Param(raw, value):
                if not SQLITE3_VALID_UNQUOTED_IDENTIFIER_RE.fullmatch(raw):
                    # NOTE could slugify this expr, eg 'num + b' -> 'num_plus_b'
                    raw = 'expr'
                param_counts[(raw, value)] += 1
                count = param_counts[(raw, value)]
                name = raw if count == 1 else f'{raw}_{count}'
                bindings[name] = value
                text.append(f':{name}')
            case SQL(subparts):
                text.append(analyze_sql(subparts, bindings, param_counts)[0])
    return ''.join(text), bindings


def sql(*args: str | Thunk) -> SQL:
    """Implements sql tag"""
    parts = []
    for arg in args:
        match arg:
            case str():
                parts.append(arg)
            case getvalue, raw, _, _:
                match value := getvalue():
                    case SQL() | Identifier():
                        parts.append(value)
                    case _:
                        parts.append(Param(raw, value))
    return SQL(parts)


# Based on examples in:
# https://docs.python.org/3/library/sqlite3.html
# https://dev.mysql.com/doc/refman/8.0/en/with.html#common-table-expressions-recursive-fibonacci-series

def demo():
    table_name = 'lang'
    name = 'C'
    date = 1972

    with sqlite3.connect(':memory:') as conn:
        cur = conn.cursor()
        cur.execute(*sql'create table {Identifier(table_name)} (name, first_appeared)')
        cur.execute(*sql'insert into lang values ({name}, {date})')
        assert set(cur.execute('select * from lang')) == {('C', 1972)}

        try:
            # Verify that not using an identifier will result in an
            # incorrect usage of placeholders
            cur.execute(*sql'drop table {table_name}')
            assert 'Did not raise error'
        except sqlite3.OperationalError:
            pass

        num = 50
        num_results = 9  # actually using num_results + 1, or 10
        
        # NOTE: separating out these queries like this probably doesn't
        # make it easier to read, but at least we can show the subquery
        # aspects work as expected, including placeholder usage.
        base_case = sql'select 1, 0, 1'
        inductive_case = sql"""
            select n + 1, next_fib_n, fib_n + next_fib_n
                from fibonacci where n < {num}
            """

        results = cur.execute(*sql"""
            with recursive fibonacci (n, fib_n, next_fib_n) AS
                (
                    {base_case}
                    union all
                    {inductive_case}
                )
                select n, fib_n from fibonacci
                order by n
                limit {num_results + 1}
            """)
        assert set(results) == \
             {(1, 0), (2, 1), (3, 1), (4, 2), (5, 3),
              (6, 5), (7, 8), (8, 13), (9, 21), (10, 34)}



def demo_sqlalchemy():
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
    except ImportError:
        print("""
Install the following packages to see this demo:
- pip install greenlet>=2.0.0a2  # minimum version that works with Python 3.12 dev
- pip install sqlalchemy
""")
    engine = create_engine("sqlite://", echo=True, future=True)
    with Session(engine) as session:
        num = 50
        num_results = 9  # actually using num_results + 1, or 10

        base_case = sql'select 1, 0, 1'
        inductive_case = sql"""
            select n + 1, next_fib_n, fib_n + next_fib_n
                from fibonacci where n < {num}
            """

        statement = sql"""
            with recursive fibonacci (n, fib_n, next_fib_n) AS
                (
                    {base_case}
                    union all
                    {inductive_case}
                )
                select n, fib_n from fibonacci
                order by n
                limit {num_results + 1}
            """

        sa_stmt = statement.to_sqlalchemy()
        results = session.execute(sa_stmt)
        assert set(results) == \
             {(1, 0), (2, 1), (3, 1), (4, 2), (5, 3),
              (6, 5), (7, 8), (8, 13), (9, 21), (10, 34)}


if __name__ == '__main__':
    demo()
    demo_sqlalchemy()
