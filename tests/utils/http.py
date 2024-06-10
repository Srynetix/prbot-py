import json
from typing import Any, Callable, Iterable, Self, TypeVar

from httpx import Request, Response
from pydantic import BaseModel, RootModel

from prbot.modules.http.client import HttpClient
from tests.utils.expect import Expectation, ExpectationHandler

ModelT = TypeVar("ModelT", bound=BaseModel)


class HttpExpectation(Expectation):
    def __init__(self) -> None:
        super().__init__()
        self._input["method"] = None
        self._input["url"] = None
        self._input["body"] = None
        self._input["params"] = None
        self._input["json"] = None
        self._output["status"] = None
        self._output["content"] = None
        self._output["exception"] = None

    def with_input_method(self, method: str) -> Self:
        self._input["method"] = method
        return self

    def with_input_url(self, url: str) -> Self:
        self._input["url"] = url
        return self

    def with_input_body(self, body: bytes) -> Self:
        self._input["body"] = body
        return self

    def with_input_json(self, json: dict[str, Any]) -> Self:
        self._input["json"] = json
        return self

    def with_input_params(self, **params: Any) -> Self:
        self._input["params"] = params
        return self

    def with_output_status(self, status: int) -> Self:
        self._output["status"] = status
        return self

    def with_output_content(self, content: bytes) -> Self:
        self._output["content"] = content
        return self

    def with_output_json(self, data: dict[str, Any]) -> Self:
        self._output["content"] = json.dumps(data).encode("utf-8")
        return self

    def with_output_json_fn(self, fn: Callable[..., dict[str, Any]]) -> Self:
        self._output["content"] = fn
        return self

    def with_output_model(self, base_model: BaseModel) -> Self:
        self._output["content"] = base_model.model_dump_json().encode("utf-8")
        return self

    def with_output_models(self, base_models: Iterable[ModelT]) -> Self:
        self._output["content"] = (
            RootModel(root=list(base_models)).model_dump_json().encode("utf-8")
        )
        return self

    def with_output_exception(self, exception: Exception) -> Self:
        self._output["exception"] = exception
        return self


class FakeHttpClient(HttpClient):
    _expectations: ExpectationHandler[HttpExpectation]

    def __init__(self) -> None:
        self._expectations = ExpectationHandler()

    def expect(self, expectation: HttpExpectation) -> Self:
        self._expectations.add(expectation)
        return self

    async def aclose(self) -> None:
        self._expectations.check_remaining_expectations()

    def clear_expectations(self) -> None:
        self._expectations.clear()

    def set_authentication_token(self, token: str) -> None: ...

    def configure(self, *, headers: dict[str, Any], base_url: str) -> None: ...

    async def request(
        self,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Response:
        found_expectation = self._expectations.get(
            method=method, url=path, body=body, json=json, params=params
        )
        found_expectation.use()

        if found_expectation._output["exception"]:
            raise found_expectation._output["exception"]

        content = found_expectation._output["content"]
        if callable(content):
            content = content()

        return Response(
            status_code=found_expectation._output["status"],
            request=Request(method=method, url=path),
            content=content,
        )
