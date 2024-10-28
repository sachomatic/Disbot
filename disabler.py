from typing import Callable, NoReturn


def disable(__cls: Callable, /) -> Callable[[], NoReturn]:
    def raiser():
        raise NotImplementedError
    return raiser