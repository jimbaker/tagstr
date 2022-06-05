# NOTE: got to support re as a prefix for this specific example (so `import re
# as re_module`)!
#
# But in practice the combination of interpolation support along with using
# functionality like re.VERBOSE might make this module actually useful with some
# more work.

import re as re_module
import string

from taglib import Thunk


def re(*args: str | Thunk) -> re_module.Pattern:
    pattern = []
    for arg in args:
        match arg:
            case str():
                pattern.append(arg)
            case getvalue, _, _, formatspec:
                pattern.append(format(getvalue(), '' if formatspec is None else formatspec))

    return re_module.compile(''.join(pattern), re_module.VERBOSE)


def demo():
    line = string.printable

    print(re'a.*z'.search(line))

    chunk = 'efg'
    print(re'a.*{chunk}'.search(line))


if __name__ == '__main__':
    demo()
