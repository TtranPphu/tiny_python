from argparse import ArgumentParser, Namespace
from tiny_python.abcs import WillLogAttrChanges


class ArgumentsBase(WillLogAttrChanges):
    __parser: ArgumentParser

    _defined_positional_arguments: dict = {}
    _defined_keyword_arguments: dict = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__parser = ArgumentParser()
        for name, options in self._defined_positional_arguments.items():
            self.__parser.add_argument(name, **options)
        for name, options in self._defined_keyword_arguments.items():
            self.__parser.add_argument(name, **options)

        arguments: Namespace = self.__parser.parse_args()
        self.logger.debug(f"Parsed arguments: {arguments}")
        for key, value in vars(arguments).items():
            setattr(self, key, value)


class ExampleArguments(ArgumentsBase):
    _defined_positional_arguments = {
        "example_arg": {
            "type": str,
            "help": "An example positional argument.",
        },
    }

    _defined_keyword_arguments = {
        "--example_kwarg": {
            "type": int,
            "default": 69,
            "help": "An example keyword argument with a default value of 69.",
        },
    }
