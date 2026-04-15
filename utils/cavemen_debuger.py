from itertools import chain
from functools import wraps
from typing import Callable


class cavemen_debuger:
    @staticmethod
    def log(*args, **kwargs):
        stack_level = kwargs.pop("stack_level", 3)
        formatter = cavemen_debuger.CavemenFormatter
        for i, v in chain(enumerate(args), kwargs.items()):
            print(formatter(i, v, stack_level=stack_level).trim().shrink())

    @staticmethod
    def full_log(*args, **kwargs):
        stack_level = kwargs.pop("stack_level", 3)
        formatter = cavemen_debuger.CavemenFormatter
        for i, v in chain(enumerate(args), kwargs.items()):
            print(formatter(i, v, stack_level=stack_level).trim())

    @staticmethod
    def raw_log(*args, **kwargs):
        stack_level = kwargs.pop("stack_level", 3)
        log_lines = cavemen_debuger.full_log
        formatter = cavemen_debuger.CavemenFormatter
        for i, v in chain(enumerate(args), kwargs.items()):
            if isinstance(v, str):
                log_lines(*str(v).splitlines(), stack_level=stack_level + 1)
            else:
                print(formatter(i, v, stack_level=stack_level))

    @staticmethod
    def waiting(message: str):
        from colorama import Fore, Style
        from os import get_terminal_size

        message = f"> Waiting on {message} ..."
        terminal_width = get_terminal_size().columns
        last_line_length = len(message) % terminal_width
        filled = f"{message}{' ' * (terminal_width - last_line_length - 1)}"
        styled = f"{Fore.YELLOW}{filled}\r{Style.RESET_ALL}"
        print(styled, end="", flush=True)

    @staticmethod
    def trace(done_message: str | None = None):
        """
        A decorator to trace the execution of a function.
        """

        def wrapper(args, kwargs):
            return (
                [f'"{a}"' if isinstance(a, str) else a for a in args],
                {k: f'"{v}"' if isinstance(v, str) else v for k, v in kwargs.items()},
            )

        def dumper(args, kwargs):
            return ", ".join(
                [str(a) for a in args] + [f"{k}={v}" for k, v in kwargs.items()]
            )

        def decorator(func: Callable):
            @wraps(func)
            def inner(*args, **kwargs):
                trim = cavemen_debuger.trim
                shink = cavemen_debuger.shrink
                func_signature = f"{func.__name__}({dumper(*wrapper(args, kwargs))})"
                print(trim(shink(f"Calling {func_signature}")))
                result = func(*args, **kwargs)
                print(trim(shink(done_message))) if done_message else None
                return result

            return inner

        return decorator

    @staticmethod
    def format(i, v, log_level: str = "CMD", stack_level: int = 2, devider: str = ": "):
        from inspect import stack
        from .file_system import file_system_status as fss

        __LOG_PATTERN = "{file}:{line} | {func} | [{level}] | {message}"

        if i is None:
            message = f"{v}"
        elif isinstance(i, str):
            message = f"'{i}'{devider}{v}"
        else:
            message = f"[{i}]{devider}{v}"

        frames = stack()[stack_level:]
        print(frames)
        frame = frames[0]

        message = __LOG_PATTERN.format(
            file=fss.rel(frame.filename),
            line=frame.lineno,
            func=frame.function,
            level=log_level,
            message=message,
        )

        return message

    @staticmethod
    def trim(message: str) -> str:
        """
        Trim the message by removing newlines and extra spaces.
        """
        from re import sub

        return sub(r"\s+", " ", message.replace("\n", " ")).strip()

    @staticmethod
    def shrink(message: str, max: int = 500, head: int = 360, tail: int = 120) -> str:
        """
        Shrink the message by keeping the head and tail
        and replacing the middle with " . . . ".
        """
        if len(message) <= max:
            return message

        return message[:head] + " . . . " + message[-tail:]

    class CavemenFormatter:
        def __init__(self, *args, **kwargs):
            self.message = cavemen_debuger.format(*args, **kwargs)

        def trim(self):
            self.message = cavemen_debuger.trim(self.message)
            return self

        def shrink(self, *args, **kwargs):
            self.message = cavemen_debuger.shrink(self.message, *args, **kwargs)
            return self

        def __str__(self):
            return self.message

        def __repr__(self):
            return self.message
