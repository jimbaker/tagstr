import re
import sqlite3
from collections.abc import Iterable

from taglib import Thunk, decode_raw



def combine(cols):
    # Given some columns, such as
    # names = ['Fortran', 'Python', 'Go']
    # dates = [1957, 1991, 2009]
    #
    # Combine together in the correct form for executemany
    # [
    # ("Fortran", 1957),
    # ("Python", 1991),
    # ("Go", 2009),]
    col_iters = [iter(col) for col in cols]
    while True:
        try:
            yield [next(col_iter) for col_iter in col_iters]
        except StopIteration:
            break


VALUES_RE = re.compile(r'\s+values\s+\($', re.IGNORECASE)


class Qmarkify:
    def __init__(self, conn):
        self.conn = conn

    @staticmethod
    def quote_identifier(name):
        # NOTE: This quoting rule is used by the PostgreSQL and SQLite dialects,
        # and possibly others. For SQLite at least, it is guaranteed to be that
        # quoting does not change case insensitivity, so it can always be safely
        # done in the interpolation.
        s = name.replace('"', '""')  # double any quoting to escape it
        return f'"{s}"'

    def __call__(self, *args: str | Thunk):
        # This is a very limited parser. But SQL! It just might be sufficient
        # for the limited aspect we are supporting.
        #
        # FIXME add support for recursively building SQL statements, especially
        # with respect to nested subqueries.
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
                        # This executemany selection logic is brittle, and
                        # potentially flawed.
                        match value:
                            case str():
                                use_executemany[raw] = False
                            case Iterable():
                                use_executemany[raw] = True
                            case _:
                                use_executemany[raw] = False
                        values.append(value)
                    else:
                        statement.append(self.quote_identifier(value))

        stmt = ''.join(statement)
        print(f'{stmt=}, {use_executemany=}, {values=}')

        cursor = self.conn.cursor()
        if use_executemany and all(use_executemany.values()):
            return cursor.executemany(stmt, combine(values))
        elif any(use_executemany.values()):
            raise ValueError('Columns must all either be a collection of values or a single value')
        else:
            return cursor.execute(stmt, values)


# Compare against the example in https://docs.python.org/3/library/sqlite3.html
def demo():
    table_name = 'lang'
    name = 'C'
    date = 1972

    names = ['Fortran', 'Python', 'Go']
    dates = [1957, 1991, 2009]

    with sqlite3.connect(':memory:') as conn:
        sql = Qmarkify(conn)
        sql'create table {table_name} (name, first_appeared)'
        sql'insert into {table_name} values ({name}, {date})'
        sql'insert into {table_name} values ({names}, {dates})'

        cursor2 = conn.cursor()
        assert list(cursor2.execute('select * from lang')) == [('C', 1972),  ('Fortran', 1957), ('Python', 1991), ('Go', 2009)]


if __name__ == '__main__':
    demo()
