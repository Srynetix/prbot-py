from typing import Any, Generic, Self, TypeVar


class Expectation:
    _input: dict[str, Any]
    _output: dict[str, Any]
    _expected_times: int
    _used_times: int

    IGNORE = object()

    def __init__(self) -> None:
        self._input = {}
        self._output = {}
        self._expected_times = 1
        self._used_times = 0

    def with_times(self, value: int) -> Self:
        self._expected_times = value
        return self

    def with_input(self, **kwargs: Any) -> Self:
        for k, v in kwargs.items():
            self._input[k] = v
        return self

    def with_output(self, **kwargs: Any) -> Self:
        for k, v in kwargs.items():
            self._output[k] = v
        return self

    def use(self) -> None:
        self._used_times += 1

    def check(self) -> bool:
        return self._used_times == self._expected_times


ExpectationT = TypeVar("ExpectationT", bound=Expectation)


class ExpectationHandler(Generic[ExpectationT]):
    _expectations: list[ExpectationT]

    def __init__(self) -> None:
        self._expectations = []

    def add(self, expectation: ExpectationT) -> Self:
        for idx, elem in enumerate(self._expectations):
            if elem._input == expectation._input:
                self._expectations[idx] = expectation
                return self

        self._expectations.append(expectation)
        return self

    def clear(self) -> None:
        self._expectations.clear()

    def get(self, **kwargs: Any) -> ExpectationT:
        for expectation in self._expectations:
            for k, v in kwargs.items():
                exp_v = expectation._input[k]
                if exp_v != v and exp_v != Expectation.IGNORE:
                    break
            else:
                return expectation

        raise MissingExpectation(kwargs)

    def check_remaining_expectations(self) -> None:
        for expectation in self._expectations:
            if not expectation.check():
                raise ExpectationUsageMismatch(expectation)


class MissingExpectation(Exception):
    def __init__(self, inputs: dict[str, Any]) -> None:
        super().__init__(f"Missing expectation for inputs: {inputs}")


class ExpectationUsageMismatch(Exception):
    def __init__(self, expectation: Expectation) -> None:
        super().__init__(
            f"Expectation usage mismatch:\n"
            f"  Input: {expectation._input}\n"
            f"  Output: {expectation._output}\n"
            f"  Expected times: {expectation._expected_times}\n"
            f"  Used times: {expectation._used_times}"
        )
