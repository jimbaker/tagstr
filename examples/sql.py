import re
import sqlite3
from collections.abc import Iterable

from taglib import Thunk, decode_raw


def combine(cols: Iterable) -> Iterable[tuple]:
    """Combines cols of single values into a column of tuples"""
    col_iters = [iter(col) for col in cols]
    while True:
        try:
            yield tuple([next(col_iter) for col_iter in col_iters])
        except StopIteration:
            break


VALUES_RE = re.compile(r'\s+values\s+\($', re.IGNORECASE)


class Qmarkify:
    """Logic to support a `sql` tag string implementation, safe or unsafe"""
    # TODO consider changing to named placeholders instead of qmarks, especially
    # given that we have the raw expression (taking into account that the raw
    # expression might be an arbitrary expression, so need to mangle
    # accordingly).
    def __init__(self, unsafe=False):
        self.unsafe = unsafe

    @staticmethod
    def _quote_identifier(name):
        # NOTE: This quoting rule is used by the PostgreSQL and SQLite dialects,
        # and possibly others. For SQLite at least, it is also guaranteed that
        # any quoting does not change case insensitivity. This means such
        # idenitifer quoting can always be safely done in the interpolation.
        s = name.replace('"', '""')  # double any quoting to escape it
        return f'"{s}"'

    def __call__(self, *args: str | Thunk, unsafe=False):
        # NOTE this is a very limited parser. But SQL! It just might be
        # sufficient for the limited aspect we are supporting.
        #

        statement = []
        values = []
        in_values = False
        use_executemany = {}

        for arg in decode_raw(*args):
            match arg:
                case str():
                    if in_values and arg.strip() != ',':
                        in_values = False
                    statement.append(arg)
                    # We only care about '...values (' immediately before we
                    # process any interpolation(s), otherwise it can be safely
                    # ignored.
                    if VALUES_RE.search(arg):
                        in_values = True
                case getvalue, raw, _, _:
                    value = getvalue()
                    if in_values:
                        statement.append('?')
                        # This executemany selection logic seems brittle and is
                        # potentially flawed.
                        match value:
                            case str():
                                use_executemany[raw] = False
                            case Iterable():
                                use_executemany[raw] = True
                            case _:
                                use_executemany[raw] = False
                        values.append(value)
                    # FIXME Need to match against `name = {expr}` and put a placeholder
                    # in at this position
                    elif self.unsafe:
                        # This is in not a placeholder position, but we allow
                        # for it to be inserted here.
                        #
                        # FIXME add support for recursive building by *not*
                        # quoting as an identifier but this also needs tracking
                        # any placeholders used.
                        statement.append(self._quote_identifier(value))
                    else:
                        raise ValueError(f'Cannot interpolate {raw} in safe mode')

        stmt = ''.join(statement)
        print(f'{stmt=}, {use_executemany=}, {values=}')

        if use_executemany and all(use_executemany.values()):
            return stmt, combine(values)
        elif any(use_executemany.values()):
            raise ValueError('Columns must all either be a collection of values or a single value')
        else:
            return stmt, values


sql = Qmarkify()
sql_unsafe = Qmarkify(unsafe=True)


# Compare against the example in https://docs.python.org/3/library/sqlite3.html
def demo():
    table_name = 'lang'
    name = 'C'
    date = 1972

    names = ['Fortran', 'Python', 'Go']
    dates = [1957, 1991, 2009]

    with sqlite3.connect(':memory:') as conn:
        cur = conn.cursor()
        cur.execute(*sql_unsafe'create table {table_name} (name, first_appeared)')
        cur.execute(*sql_unsafe'insert into {table_name} values ({name}, {date})')
        cur.executemany(*sql'insert into lang values ({names}, {dates})')

        # FIXME time to write proper unit tests!
        # NOTE assumes that SQLite maintains insertion order (as it apparently does)
        assert list(cur.execute('select * from lang')) == \
            [('C', 1972),  ('Fortran', 1957), ('Python', 1991), ('Go', 2009)]

        try:
            cur.execute(*sql'drop table {table_name}')
            assert 'Did not raise error'
        except ValueError:
            pass


if __name__ == '__main__':
    demo()
