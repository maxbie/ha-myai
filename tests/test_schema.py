"""Regression tests for Home Assistant schema conversion.

Run with: python -m unittest discover -s tests
Requires probatio and voluptuous-openapi, without a Home Assistant installation.
"""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import probatio
import voluptuous as vol
from voluptuous_openapi import convert

spec = importlib.util.spec_from_file_location(
    "myai_schema",
    Path(__file__).resolve().parents[1] / "custom_components/myai/schema.py",
)
schema_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(schema_module)


class SchemaConversionTests(unittest.TestCase):
    def test_probatio_tools_produce_serializable_parameters(self):
        """Reproduce HA's UNSUPPORTED sentinel in the old converter."""
        schema = probatio.Schema(
            {
                probatio.Required("name"): str,
                probatio.Optional("brightness"): probatio.All(
                    int, probatio.Range(min=0, max=100)
                ),
            }
        )
        serializer = lambda value: probatio.UNSUPPORTED
        with self.assertRaises(TypeError):
            json.dumps(convert(schema, custom_serializer=serializer))

        parameters = schema_module.convert_schema(schema, serializer)
        json.dumps({"tools": [{"type": "function", "function": {
            "name": "HassLightSet", "parameters": parameters,
        }}]})
        self.assertEqual(parameters["type"], "object")
        self.assertEqual(parameters["required"], ["name"])
        self.assertEqual(parameters["properties"]["name"]["type"], "string")
        self.assertEqual(parameters["properties"]["brightness"]["maximum"], 100)

    def test_custom_selectors_keep_their_json_schema(self):
        """Preserve selector conversion for structured output and tools."""
        class TextSelector:
            pass

        selector = TextSelector()

        def serializer(value):
            if value is selector:
                return {"type": "string", "enum": ["on", "off"]}
            return probatio.UNSUPPORTED

        schema = probatio.Schema({probatio.Required("state"): selector})
        converted = schema_module.convert_schema(schema, serializer)
        self.assertEqual(
            converted["properties"]["state"],
            {"type": "string", "enum": ["on", "off"]},
        )
        json.dumps(converted)

    def test_legacy_schema_with_new_serializer(self):
        """Translate the new sentinel to the legacy converter's sentinel."""
        converted = schema_module.convert_schema(
            vol.Schema({vol.Required("name"): str}),
            lambda value: probatio.UNSUPPORTED,
        )
        self.assertEqual(converted["properties"]["name"]["type"], "string")
        json.dumps(converted)

    def test_legacy_home_assistant_without_probatio(self):
        """Keep older Home Assistant installations working."""
        with patch.object(schema_module, "probatio", None):
            converted = schema_module.convert_schema(
                vol.Schema({vol.Required("enabled"): bool})
            )
        self.assertEqual(converted["properties"]["enabled"]["type"], "boolean")
        json.dumps(converted)


if __name__ == "__main__":
    unittest.main()
