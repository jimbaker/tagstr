import shlex

from taglib import Thunk


# Minimal marker class to distinguish two classes of strings:
# 1. With this marker, this string has already been properly shell quoted and
#    can directly be used as a command, including being recursively
#    interpolated. This enables recursive construction of the shell command.
# 2. Without this marker, this string will be quoted before being interpolated.
class ShellCommand(str):
    def __new__(cls, command: list[str]):
        return super().__new__(cls, ''.join(command))


def sh(*args: str | Thunk) -> ShellCommand:
    command = []
    for arg in args:
        match arg:
            case str():
                command.append(arg)
            case getvalue, _, _, _:
                match value := getvalue():
                    case ShellCommand():
                        command.append(value)
                    case _:
                        # It may be nonsensical to stringify arbitrary values
                        # but they will be appropriately shell quoted!
                        command.append(shlex.quote(str(value)))
    return ShellCommand(command)


def demo():
    import subprocess

    for name in ['.', 'foo', 'foo; cat some/credential/data', 47, {'some': 'data'}]:
        print(sh'ls -ls {name}')
        print(sh'ls -ls $({sh"echo {name}"})')
        print(subprocess.run(sh'ls -ls {name} | (echo "First 5 results from ls:"; head -5)', shell=True, capture_output=True))


if __name__ == '__main__':
    demo()
