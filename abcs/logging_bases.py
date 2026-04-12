from logging import Logger, Handler, getLogger as get_logger

from ..utils import path_str, fss, fsm


class HasLogger:
    logger: Logger

    def __init__(self, **kwargs):
        self.__setup()
        super().__init__(**kwargs)

    def __setup(self):
        fsm.ensure_dir_exists(self._log_folder())
        self.logger = self.__logger()
        self.logger.debug(f"Logger({self._logger_name()}) initialized")

    def __logger(self) -> Logger:
        """Override this method to use custom logger."""
        from logging import DEBUG

        logger = get_logger(self._logger_name())
        if logger.hasHandlers():
            return logger

        logger.setLevel(DEBUG)

        for handler in self._log_handlers():
            logger.addHandler(handler)

        return logger

    def _logger_name(self) -> str:
        """Override this method to use custom logger name."""
        return self.__class__.__name__

    def _log_file(self) -> path_str:
        """Override this method to use custom log file."""
        return fss.join(self._log_folder(), self._logger_name(), extention="log")

    def _log_folder(self) -> path_str:
        """Override this method to use custom log folder."""
        return fss.join(fss.abs(fss.cwd()), ".logs")

    def _log_handlers(self) -> list[Handler]:
        """Override this method to use custom log handlers."""
        return [self.__default_steam_handler(), self.__default_file_handler()]

    def __default_steam_handler(self) -> Handler:
        from logging import LogRecord, StreamHandler, Formatter, DEBUG

        class DefaultSteamFormatter(Formatter):
            def format(self, record: LogRecord) -> str:
                from re import sub

                base = super().format(record)
                trimmed = sub(r" +", " ", base).replace("\n", " ")
                relative = fss.rel(record.pathname)
                return trimmed.replace(record.pathname, relative, 1)

        steam_handler = StreamHandler()
        steam_formatter = DefaultSteamFormatter(
            fmt="%(pathname)s:%(lineno)d | "
            f"{self.__class__.__name__}.%(funcName)s | [%(levelname)s] | %(message)s"
        )
        steam_handler.setFormatter(steam_formatter)
        steam_handler.setLevel(DEBUG)

        return steam_handler

    def __default_file_handler(self) -> Handler:
        from logging import Formatter, INFO
        from logging.handlers import TimedRotatingFileHandler

        class DefaultFileFormatter(Formatter):
            pass

        file_handler = TimedRotatingFileHandler(self._log_file(), when="midnight")
        file_formatter = DefaultFileFormatter(
            fmt="%(asctime)s | %(pathname)s:%(lineno)d | "
            f"{self.__class__.__name__}.%(funcName)s | [%(levelname)s] | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S %z",
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(INFO)

        return file_handler


class WillLogAttrChanges(HasLogger):
    class ObservableList(list):
        def __init__(self, parent: "WillLogAttrChanges", variable: str, *args):
            super().__init__(*args)
            self.__parent = parent
            self.__variable = variable

        def __setitem__(self, index, value):
            if hasattr(self.__parent, "logger"):
                self.__parent.logger.debug(f"{self.__variable}[{index}]: {value}")
            super().__setitem__(index, value)

        def append(self, value):
            if hasattr(self.__parent, "logger"):
                self.__parent.logger.debug(f"{self.__variable}.appended({value})")
            super().append(value)

    class ObservableDict(dict):
        def __init__(self, parent: "WillLogAttrChanges", variable: str, **kwargs):
            super().__init__(**kwargs)
            self.__parent = parent
            self.__variable = variable

        def __setitem__(self, key, value):
            if hasattr(self.__parent, "logger"):
                self.__parent.logger.debug(f"{self.__variable}[{key}]: {value}")
            super().__setitem__(key, value)

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if isinstance(value, list):
                print(f"Wrapping {key} with ObservableList")
                kwargs[key] = self.ObservableList(self, key, value)
            elif isinstance(value, dict):
                print(f"Wrapping {key} with ObservableDict")
                kwargs[key] = self.ObservableDict(self, key, **value)
        super().__init__(**kwargs)

    def __setattr__(self, name, value):
        if isinstance(value, list):
            value = self.ObservableList(self, name, value)
        elif isinstance(value, dict):
            value = self.ObservableDict(self, name, **value)
        if hasattr(self, "logger"):
            self.logger.debug(f"{name}: {value}")
        super().__setattr__(name, value)

