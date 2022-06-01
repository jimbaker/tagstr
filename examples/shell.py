import shlex
from dataclasses import dataclass

from taglib import Thunk, decode_raw


@dataclass
class ShellCommand:
    command: list[str]

    def __str__(self):
        return ''.join(self.command)

    def __iter__(self):
        # NOTE: subprocess.run will happily consume an iterator of string args.
        # This support lets us avoid having the user to explicitly doing `str`,
        # that is with something like `subprocess.run(str(shell"..."), ...`
        # Standard shell quoting is maintained. This seems like a nice
        # convenience.
        return iter([str(self)])


def sh(*args: str | Thunk) -> ShellCommand:
    command = []
    for arg in decode_raw(*args):
        match arg:
            case str():
                command.append(arg)
            case getvalue, *_:
                value = getvalue()
                match value:
                    case ShellCommand():
                        # Enables recursive construction of the shell command
                        command.append(str(value))
                    case _:
                        command.append(shlex.quote(str(getvalue())))
    return ShellCommand(command)


def useit():
    import subprocess

    name = 'foo; cat some/credential/data'
    print(sh'ls -ls {name}')
    print(sh'ls -ls $({sh"echo {name}"})')
    print(subprocess.run(sh'ls -ls {name} | (echo "First 5 results from ls:"; head -5)', shell=True, capture_output=True))


if __name__ == '__main__':
    useit()
