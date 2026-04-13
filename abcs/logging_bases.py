from logging import Logger, Handler, Formatter, getLogger as get_logger

from ..utils import path_str, file_system_status as fss, file_system_manipulation as fsm


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

    def __init__(self, **kwargs):
        self.__setup()
        super().__init__(**kwargs)

    def __setup(self):
        fsm.ensure_dir_exists(self._log_folder())
        self.logger = self.__logger()
        self.logger.debug(
            f"{self.logger.__class__.__name__}({self._logger_name()}) initialized"
        )

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
    _S = {}
    _M = {}

    def wrap(self, manager: "WillLogAttrChanges", variable: str, value):
        def __log(t):
            if hasattr(manager, "logger"):
                manager.logger.debug(f"Wrapping {variable} as {t}")

        if (__t := type(value)) in self._M:
            for k, v in value.items():
                value[k] = self.wrap(manager, f"{variable}[{k}]", v)
            __log(self._M[__t].__name__)
            return self._M[__t](manager, variable, **value)
        elif (__t := type(value)) in self._S:
            for i, v in enumerate(value):
                value[i] = self.wrap(manager, f"{variable}[{i}]", v)
            __log(self._S[__t].__name__)
            return self._S[__t](manager, variable, *value)
        return value

    class ObservableList(list):
        def __init__(self, manager: "WillLogAttrChanges", variable: str, *args):
            super().__init__(*args)
            self.__manager = manager
            self.__variable = variable

        def __setitem__(self, index, value):
            value = self.__manager.wrap(
                manager=self.__manager,
                variable=f"{self.__variable}[{index}]",
                value=value,
            )
            if hasattr(self.__manager, "logger"):
                self.__manager.logger.debug(f"{self.__variable}[{index}] = {value}")
            super().__setitem__(index, value)

        def append(self, value):
            value = self.__manager.wrap(
                manager=self.__manager,
                variable=f"{self.__variable}[{len(self)}]",
                value=value,
            )
            if hasattr(self.__manager, "logger"):
                self.__manager.logger.debug(f"{self.__variable}[{len(self)}] = {value}")
            super().append(value)

    class ObservableDict(dict):
        def __init__(self, manager: "WillLogAttrChanges", variable: str, **kwargs):
            super().__init__(**kwargs)
            self.__manager = manager
            self.__variable = variable

        def __setitem__(self, key, value):
            value = self.__manager.wrap(
                manager=self.__manager,
                variable=f"{self.__variable}[{key}]",
                value=value,
            )
            if hasattr(self.__manager, "logger"):
                self.__manager.logger.debug(f"{self.__variable}[{key}] = {value}")
            super().__setitem__(key, value)

    def __init__(self, **kwargs):
        self._S.update({list: self.ObservableList})
        self._M.update({dict: self.ObservableDict})
        for key, value in kwargs.items():
            if key.startswith("_"):
                continue
            kwargs[key] = self.wrap(
                manager=self,
                variable=key,
                value=value,
            )

        super().__init__(**kwargs)

    def __setattr__(self, name, value):
        value = self.wrap(
            manager=self,
            variable=name,
            value=value,
        )
        if hasattr(self, "logger"):
            self.logger.debug(f"{name} = {value}")
        super().__setattr__(name, value)
