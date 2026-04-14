from functools import wraps
from typing import Callable, TypeVar, Optional


R = TypeVar("R")


class CriticalException(Exception):
    pass


class ErrorException(Exception):
    pass


class WarningException(Exception):
    pass


class IgnoredException(Exception):
    pass


class no_exception:
    @staticmethod
    def error_for_exception(func: Callable[..., R]) -> Callable[..., R | Exception]:
        """
        Decorator to catch exceptions in a function
        and return the exception instead of raising it.
        """
        from functools import partial

        print_stack = partial(no_exception.print_stack, _as=None)

        @wraps(func)
        def decorator(*args, **kwargs):
            from sys import exit

            result = no_exception.try_execute(func)(*args, **kwargs)
            print_stack(result) if isinstance(result, Exception) else None
            exit() if isinstance(result, CriticalException) else None

            return result

        return decorator

    def critical_error_for_exception(func: Callable[..., R]) -> Callable[..., R]:
        """
        Decorator to catch exceptions in a function
        and exit the program if an exception occurs.
        """
        from functools import partial

        print_stack = partial(no_exception.print_stack, _as=CriticalException())

        @wraps(func)
        def decorator(*args, **kwargs):
            from sys import exit

            result = no_exception.try_execute(func)(*args, **kwargs)
            print_stack(result) if isinstance(result, Exception) else None
            exit() if isinstance(result, Exception) else None

            return result

        return decorator

    @staticmethod
    def warning_for_exception(func: Callable[..., None]) -> Callable[..., None]:
        """
        Decorator to catch exceptions in a function
        and log a warning if an exception occurs.
        """
        from functools import partial

        print_stack = partial(no_exception.print_stack, _as=WarningException())

        @wraps(func)
        def decorator(*args, **kwargs):
            result = no_exception.try_execute(func)(*args, **kwargs)
            print_stack(result) if isinstance(result, Exception) else None

        return decorator

    @staticmethod
    def ignore_exception(func: Callable[..., None]) -> Callable[..., None]:
        """
        Decorator to catch exceptions in a function
        and ignore them.
        """
        from functools import partial

        print_stack = partial(no_exception.print_stack, _as=IgnoredException())

        @wraps(func)
        def decorator(*args, **kwargs):
            result = no_exception.try_execute(func)(*args, **kwargs)
            print_stack(result) if isinstance(result, Exception) else None

        return decorator

    @staticmethod
    def default_for_exception(default: R):
        """
        Decorator to catch exceptions in a function,
        and return a default value if an exception occurs.
        """
        from functools import partial

        print_stack = partial(no_exception.print_stack, _as=WarningException())

        def decorator(func: Callable[..., R]) -> Callable[..., R]:
            @wraps(func)
            def inner(*args, **kwargs):
                result = no_exception.try_execute(func)(*args, **kwargs)
                print_stack(result) if isinstance(result, Exception) else None

                return default if isinstance(result, Exception) else result

            return inner

        return decorator

    @staticmethod
    def try_execute(func: Callable[..., R]) -> Callable[..., R | Exception]:
        @wraps(func)
        def decorator(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as exception:
                return exception

        return decorator

    @staticmethod
    def print_stack(exception: Exception, _as: Optional[Exception] = None):
        from types import FrameType
        from .file_system import file_system_status as fss
        from inspect import getargvalues
        from colorama import Fore, Back, Style

        __DCRT = f"{Back.RESET}{Fore.LIGHTMAGENTA_EX}{Style.DIM}"
        __DERR = f"{Back.RESET}{Fore.LIGHTRED_EX}{Style.DIM}"
        __DWRN = f"{Back.RESET}{Fore.LIGHTYELLOW_EX}{Style.DIM}"
        __DIGN = f"{Back.RESET}{Fore.LIGHTWHITE_EX}{Style.DIM}"

        __CRT = f"{Back.MAGENTA}{Fore.WHITE}"
        __ERR = f"{Back.RED}{Fore.WHITE}"
        __WRN = f"{Back.YELLOW}{Fore.WHITE}"
        __IGN = f"{Back.RESET}{Fore.RESET}{Style.DIM}"

        if _as is None:
            _as = type(exception)()

        def format(message: str) -> str:
            from re import sub

            return sub(r" +", " ", message).replace("\n", " ")

        if isinstance(_as, CriticalException):
            header_style = __CRT
            style = __DCRT
        elif isinstance(_as, WarningException):
            header_style = __WRN
            style = __DWRN
        elif isinstance(_as, IgnoredException):
            header_style = __IGN
            style = __DIGN
        else:
            header_style = __ERR
            style = __DERR

        print(
            f"{header_style}"
            f"{exception.__class__.__name__}({exception})"
            f"{Style.RESET_ALL}"
        )

        frames: list[FrameType] = []
        trace = exception.__traceback__
        while trace:
            frame = trace.tb_frame
            fn_name = frame.f_code.co_name
            frames.append(frame) if fn_name not in [
                "decorator",
                "trace",
                "inner",
                "outter",
            ] else None
            trace = trace.tb_next

        for frame in reversed(frames):
            file_name = frame.f_code.co_filename.replace(fss.cwd(), "./", 1)
            line_no = frame.f_lineno
            fn_name = frame.f_code.co_name
            _fn = getargvalues(frame)
            fn_kwargs = [
                f"{k}={v!r}"
                for k, v in _fn.locals.items()
                if k in _fn.args
                if k != "self"
            ]
            message = format(
                f"from {file_name}:{line_no} | {fn_name}({', '.join(fn_kwargs)})"
            )
            print(f"  {style}{message}{Style.RESET_ALL}")
