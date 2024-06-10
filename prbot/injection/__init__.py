from typing import Type, TypeVar

import inject
import structlog

logger = structlog.get_logger(__name__)
TBound = TypeVar("TBound")


def inject_instance(bound_class: Type[TBound]) -> TBound:
    return inject.instance(bound_class)
