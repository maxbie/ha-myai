"""Convert Home Assistant schemas with the matching schema library."""
from __future__ import annotations

from typing import Any, Callable

import voluptuous_openapi

try:
    import probatio
except ImportError:  # Home Assistant versions before the probatio migration.
    probatio = None


def convert_schema(
    schema: Any, custom_serializer: Callable[[Any], Any] | None = None
) -> dict[str, Any]:
    """Support probatio schemas and legacy voluptuous schemas."""
    if probatio is not None and isinstance(schema, probatio.Schema):
        return probatio.to_openapi(schema, custom_serializer=custom_serializer)

    def legacy_serializer(value: Any) -> Any:
        result = custom_serializer(value)
        # Each schema library has its own unsupported sentinel.
        if probatio is not None and result is probatio.UNSUPPORTED:
            return getattr(voluptuous_openapi, "UNSUPPORTED", None)
        return result

    return voluptuous_openapi.convert(
        schema, custom_serializer=legacy_serializer if custom_serializer else None
    )
