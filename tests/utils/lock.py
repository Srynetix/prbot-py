from contextlib import asynccontextmanager
from typing import AsyncGenerator, Callable, Self

from prbot.modules.lock import LockClient, LockException
from tests.utils.expect import Expectation, ExpectationHandler


class MissingExpectation(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Missing expectation: {name}")


class LockExpectation(Expectation):
    def __init__(self) -> None:
        super().__init__()
        self._input["action"] = None
        self._output["function"] = None

    def with_input_action(self, action: str) -> Self:
        self._input["action"] = action
        return self

    def with_output_function(self, function: Callable[..., None]) -> Self:
        self._output["function"] = function
        return self

    def with_output_function_as_once_lock(self) -> Self:
        lock_status = False

        def lock_fn(k: str) -> None:
            nonlocal lock_status
            if lock_status is False:
                lock_status = True
            else:
                raise RuntimeError("Already locked")

        self._output["function"] = lock_fn
        return self


class FakeLockClient(LockClient):
    _expectations: ExpectationHandler[LockExpectation]

    def __init__(self) -> None:
        self._expectations = ExpectationHandler()

    def expect(self, expectation: LockExpectation) -> Self:
        self._expectations.add(expectation)
        return self

    def clear_expectations(self) -> None:
        self._expectations.clear()

    async def aclose(self) -> None:
        self._expectations.check_remaining_expectations()

    async def ping(self) -> bool:
        ping_exp = self._expectations.get(action="ping")
        ping_exp.use()
        return bool(ping_exp._output["function"]())

    @asynccontextmanager
    async def lock(self, key: str) -> AsyncGenerator[None, None]:
        lock_exp = self._expectations.get(action="lock")
        lock_exp.use()

        try:
            lock_exp._output["function"](key)
            yield
        except Exception as exc:
            raise LockException(str(exc)) from exc
