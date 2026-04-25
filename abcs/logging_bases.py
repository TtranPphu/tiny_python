from ..utils import (
    file_system_manipulation as fsm,
    file_system_status as fss,
    path_str,
)

from logging import Logger, Handler, Formatter, getLogger as get_logger
from pandas import DataFrame
from pandas.core.indexing import _LocIndexer, _iLocIndexer
from typing import Optional


class DefaultLogger(Logger):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _log(self, *args, **kwargs):
        import traceback

        stack = traceback.extract_stack()
        stacklevel = kwargs.pop("stacklevel", 1)
        stacklevel += 1

        for frame in reversed(stack[:-2]):
            if frame.filename != __file__:
                break
            stacklevel += 1

        kwargs["stacklevel"] = stacklevel
        return super()._log(*args, **kwargs)


class HasLogger:
    logger: Logger

    def __init__(self, *args, **kwargs):
        self.__setup()
        super().__init__(*args, **kwargs)

    def __setup(self):
        fsm.ensure_dir_exists(self._log_folder())
        self.logger = self.__logger()
        __logger_class = self.logger.__class__.__name__
        __logger_name = self._logger_name()
        self.logger.debug(f"{__logger_class}({__logger_name}) initialized")

    def __logger(self) -> Logger:
        from logging import DEBUG

        logger = DefaultLogger(get_logger(self._logger_name()))
        if logger.hasHandlers():
            return logger

        logger.setLevel(DEBUG)

        for handler in self._log_handlers():
            logger.addHandler(handler)

        return logger

    def _logger_name(self) -> str:
        """Override this method to use custom logger name."""
        return self.__class__.__name__

    def _log_handlers(self) -> list[Handler]:
        """Override this method to use custom log handlers."""
        return [self.__default_steam_handler(), self.__default_file_handler()]

    def _log_folder(self) -> path_str:
        """Override this method to use custom log folder."""
        return fss.join(fss.abs(fss.cwd()), ".logs")

    def _log_file(self) -> path_str:
        """Override this method to use custom log file."""
        return fss.join(self._log_folder(), self._logger_name(), extention="log")

    class DefaultFormatter(Formatter):
        def format(self, record):
            from re import sub

            base = super().format(record)
            trimmed = sub(r" +", " ", base).replace("\n", " ")
            relative = fss.rel(record.pathname)
            return trimmed.replace(record.pathname, relative, 1)

    def __default_steam_handler(self) -> Handler:
        from logging import StreamHandler, DEBUG

        class DefaultSteamFormatter(self.DefaultFormatter):
            pass

        steam_handler = StreamHandler()
        steam_formatter = DefaultSteamFormatter(
            fmt="%(pathname)s:%(lineno)d | "
            f"{self.__class__.__name__} | %(funcName)s | "
            "[%(levelname)s] | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S %z",
        )
        steam_handler.setFormatter(steam_formatter)
        steam_handler.setLevel(DEBUG)

        return steam_handler

    def __default_file_handler(self) -> Handler:
        from logging import INFO
        from logging.handlers import TimedRotatingFileHandler

        class DefaultFileFormatter(self.DefaultFormatter):
            pass

        file_handler = TimedRotatingFileHandler(self._log_file(), when="midnight")
        file_formatter = DefaultFileFormatter(
            fmt="%(asctime)s | %(pathname)s:%(lineno)d | "
            f"{self.__class__.__name__} | %(funcName)s | "
            "[%(levelname)s] | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S %z",
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(INFO)

        return file_handler


class WillLogAttrChanges(HasLogger):
    _ObservableMappings: dict[type, type]
    _ObservableFrames: dict[type, type]
    _ObservableSequences: dict[type, type]

    @classmethod
    def wrap(cls, value, observer: "WillLogAttrChanges", variable: str):
        def __log(type_name: str):
            msg = (
                f"Wrapping {variable} as "
                f"{type_name}(observer={observer.__class__.__name__}<{id(observer)}>)"
            )
            if hasattr(observer, "logger"):
                observer.logger.debug(msg)
                pass

        if (__type := type(value)) in cls._ObservableMappings:
            for k, v in value.items():
                value[k] = cls.wrap(v, observer, f"{variable}[{k}]")
            CustomMapping = cls._ObservableMappings[__type]
            __log(type_name=CustomMapping.__name__)
            return CustomMapping(**value, observer=observer, variable=variable)

        elif __type in cls._ObservableFrames:
            for c, v in value.items():
                value[c] = cls.wrap(observer, f"{variable}[{c}]", v)
            CustomFrame = cls._ObservableFrames[__type]
            __log(type_name=CustomFrame.__name__)
            return CustomFrame(value, observer=observer, variable=variable)

        elif __type in cls._ObservableSequences:
            for i, v in enumerate(value):
                value[i] = cls.wrap(v, observer, f"{variable}[{i}]")
            CustomSequence = cls._ObservableSequences[__type]
            __log(type_name=CustomSequence.__name__)
            return CustomSequence(*value, observer=observer, variable=variable)

        return value

    class ObservableList(list):
        __observer: Optional["WillLogAttrChanges"]

        def __init__(self, *args, **kwargs):
            self.__observer = kwargs.pop("observer", None)
            self.__variable = kwargs.pop("variable", r"_")
            super().__init__(*args, **kwargs)

        def __setitem__(self, index, value):
            if self.__observer is None:
                return super().__setitem__(index, value)

            __variable = f"{self.__variable}[{index}]"
            value = self.__observer.wrap(
                value=value,
                observer=self.__observer,
                variable=__variable,
            )
            if hasattr(self.__observer, "logger"):
                self.__observer.logger.debug(f"{__variable} = {value}")
            return super().__setitem__(index, value)

        def append(self, value):
            if self.__observer is None:
                return super().append(value)

            __variable = f"{self.__variable}[{len(self)}]"
            value = self.__observer.wrap(
                value=value,
                observer=self.__observer,
                variable=__variable,
            )

            if hasattr(self.__observer, "logger"):
                self.__observer.logger.debug(f"{__variable} = {value}")

            return super().append(value)

    class ObservableDict(dict):
        __observer: Optional["WillLogAttrChanges"]

        def __init__(self, *args, **kwargs):
            self.__observer = kwargs.pop("observer", None)
            self.__variable = kwargs.pop("variable", r"_")
            super().__init__(*args, **kwargs)

        def __setitem__(self, key, value):
            if self.__observer is None:
                return super().__setitem__(key, value)

            value = self.__observer.wrap(
                value=value,
                observer=self.__observer,
                variable=f"{self.__variable}[{key}]",
            )

            if hasattr(self.__observer, "logger"):
                self.__observer.logger.debug(f"{self.__variable}[{key}] = {value}")

            return super().__setitem__(key, value)

    class _ObservableIndexerBase:
        __observer: Optional["WillLogAttrChanges"]

        def __init__(self, *args, **kwargs):
            self.__observer = kwargs.pop("observer", None)
            self.__variable = kwargs.pop("variable", r"_")
            super().__init__(*args, **kwargs)

        def _wrap_and_log(self, key, value, kind: str):
            if self.__observer is None:
                return value

            target = f"{self.__variable}.{kind}[{key}]"
            __wp = {"value": value, "observer": self.__observer, "variable": target}
            value = self.__observer.wrap(**__wp)

            if hasattr(self.__observer, "logger"):
                self.__observer.logger.debug(f"{target} = {value}")

            return value

    class _ObservableLocIndexer(_ObservableIndexerBase, _LocIndexer):
        def __setitem__(self, key, value):
            value = self._wrap_and_log(key=key, value=value, kind="loc")
            return super().__setitem__(key, value)

    class _ObservableILocIndexer(_ObservableIndexerBase, _iLocIndexer):
        def __setitem__(self, key, value):
            value = self._wrap_and_log(key=key, value=value, kind="iloc")
            return super().__setitem__(key, value)

    class ObservableDataFrame(DataFrame):
        __observer: Optional["WillLogAttrChanges"]
        __variable: str
        _metadata = [
            "_ObservableDataFrame__observer",
            "_ObservableDataFrame__variable",
        ]

        def __init__(self, *args, **kwargs):
            __observer = kwargs.pop("observer", None)
            __variable = kwargs.pop("variable", r"_")
            super().__init__(*args, **kwargs)
            object.__setattr__(self, "_ObservableDataFrame__observer", __observer)
            object.__setattr__(self, "_ObservableDataFrame__variable", __variable)

        def __finalize__(self, other, method=None, **kwargs):
            for attr in self._metadata:
                object.__setattr__(self, attr, getattr(other, attr, None))
            return self

        @property
        def _constructor(self):
            return WillLogAttrChanges.ObservableDataFrame

        @property
        def loc(self):
            __p = {"observer": self.__observer, "variable": self.__variable}
            return WillLogAttrChanges._ObservableLocIndexer("loc", self, **__p)

        @property
        def iloc(self):
            __p = {"observer": self.__observer, "variable": self.__variable}
            return WillLogAttrChanges._ObservableILocIndexer("iloc", self, **__p)

        def isetitem(self, loc, value):
            if self.__observer is None:
                return super().isetitem(loc, value)

            value = self.__observer.wrap(
                value=value,
                observer=self.__observer,
                variable=f"{self.__variable}[{loc}]",
            )

            if hasattr(self.__observer, "logger"):
                self.__observer.logger.debug(f"{self.__variable}[{loc}] = {value}")

            return super().isetitem(loc, value)

        def __setitem__(self, key, value):
            if self.__observer is None:
                return super().__setitem__(key, value)

            value = self.__observer.wrap(
                value=value,
                observer=self.__observer,
                variable=f"{self.__variable}[{key}]",
            )

            if hasattr(self.__observer, "logger"):
                self.__observer.logger.debug(f"{self.__variable}[{key}] = {value}")

            super().__setitem__(key, value)

        def rename(self, *args, **kwargs):
            if self.__observer is None:
                return super().rename(*args, **kwargs)

            if self.__observer.logger:
                message = "{v}.rename({p})"
                __v = self.__variable
                __a = list(args) + [f"{k}={v}" for k, v in kwargs.items()]
                __p = f"{', '.join(__a)}"
                self.__observer.logger.debug(message.format(v=__v, p=__p))

            return super().rename(*args, **kwargs)

        def drop(self, *args, **kwargs):
            if self.__observer is None:
                return super().drop(*args, **kwargs)

            if self.__observer.logger:
                __v = self.__variable
                __a = list(args) + [f"{k}={v}" for k, v in kwargs.items()]
                __p = f"{', '.join(__a)}"
                message = "{v}.drop({p})"
                self.__observer.logger.debug(message.format(v=__v, p=__p))

            return super().drop(*args, **kwargs)

    _ObservableSequences = {
        list: ObservableList,
        ObservableList: ObservableList,
    }
    _ObservableMappings = {
        dict: ObservableDict,
        ObservableDict: ObservableDict,
    }
    _ObservableFrames = {
        DataFrame: ObservableDataFrame,
        ObservableDataFrame: ObservableDataFrame,
    }

    def __init__(self, *args, **kwargs):

        for key, value in [(k, v) for k, v in kwargs.items() if not k.startswith("_")]:
            kwargs[key] = self.wrap(value=value, observer=self, variable=key)
        super().__init__(*args, **kwargs)

    def __setattr__(self, name, value):
        value = self.wrap(value=value, observer=self, variable=name)
        if hasattr(self, "logger"):
            self.logger.debug(f"{name} = {value}")
        super().__setattr__(name, value)
