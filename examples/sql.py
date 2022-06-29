import re
import sqlite3
from typing import Any, NamedTuple

from taglib import Thunk


# NOTE: other dialects have different rules, for example Postgres
# allows for Unicode in the unquoted identifier, per the docs.
SQLITE3_VALID_UNQUOTED_IDENTIFIER_RE = re.compile(r'[a-z_][a-z0-9_]*')


def _quote_identifier(name: str) -> str:
    if not name:
        raise ValueError("Identifiers cannot be an empty string")
    elif SQLITE3_VALID_UNQUOTED_IDENTIFIER_RE.match(name):
        # Do not quote if possible
        return name
    else:
        s = name.replace('"', '""')  # double any quoting to escape it
        return f'"{s}"'


class SQL(NamedTuple):
    sql: str
    parameters: dict[str, Any]


class Identifier(str):
    def __new__(cls, name):
        return super().__new__(cls, _quote_identifier(name))


def sql(*args: str | Thunk) -> SQL:
    parts = []
    parameters = {}

    for arg in args:
        match arg:
            case str():
                parts.append(arg)
            case getvalue, raw, _, _:
                match value := getvalue():
                    case SQL():
                        parts.append(value.sql)
                        parameters |= value.parameters
                    case Identifier():
                        parts.append(value)
                    case _:
                        # FIXME this only works if the expression is a valid
                        # placeholder name as well - we will need some sort
                        # of "slug" scheme that preserves uniqueness,
                        # or just simple numbering
                        placeholder = f':{raw}'
                        parts.append(placeholder)
                        parameters[raw] = value

    
    return SQL(''.join(parts), parameters)


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
        num_results = 10
        
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
                limit {num_results}
            """)
        assert set(results) == \
             {(1, 0), (2, 1), (3, 1), (4, 2), (5, 3),
              (6, 5), (7, 8), (8, 13), (9, 21), (10, 34)}



if __name__ == '__main__':
    demo()
