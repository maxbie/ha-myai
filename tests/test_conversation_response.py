"""Exercise the actual conversation methods without installing Home Assistant."""
import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock

SOURCE = Path(__file__).resolve().parents[1] / "custom_components/myai/conversation.py"


def make_entity(api_result=None, api_error=None):
    source = ast.parse(SOURCE.read_text(encoding="utf-8"))
    entity_class = next(node for node in source.body if isinstance(node, ast.ClassDef))
    methods = [
        node for node in entity_class.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in {"_async_handle_message", "_call_api", "_error_content"}
    ]
    module = ast.Module(
        body=[ast.ImportFrom(module="__future__", names=[
            ast.alias(name="annotations")
        ], level=0), ast.ClassDef(
            name="Entity", bases=[], keywords=[], body=methods, decorator_list=[]
        )],
        type_ignores=[],
    )
    namespace = {
        "asyncio": asyncio,
        "aiohttp": SimpleNamespace(ClientError=ConnectionError),
        "conversation": SimpleNamespace(
            AssistantContent=lambda **kw: SimpleNamespace(**({"tool_calls": None} | kw)),
            ConverseError=RuntimeError,
            async_get_result_from_chat_log=lambda user, log: log.content[-1],
        ),
        "get_option": lambda entry, key, default: default,
        "CONF_SYSTEM_PROMPT": "prompt", "DEFAULT_SYSTEM_PROMPT": "",
        "CONF_HA_CONTROL": "control", "DEFAULT_HA_CONTROL": False,
        "DOMAIN": "myai", "MAX_TOOL_ITERATIONS": 10,
        "llm": SimpleNamespace(LLM_API_ASSIST="assist"),
        "_LOGGER": Mock(),
        "async_call_api": AsyncMock(return_value=api_result, side_effect=api_error),
    }
    exec(compile(ast.fix_missing_locations(module), str(SOURCE), "exec"), namespace)
    entity = namespace["Entity"]()
    entity._entry = SimpleNamespace()
    entity.entity_id = "conversation.myai"
    entity.hass = None
    entity._build_messages = lambda log: [{"role": "user", "content": "hello"}]
    entity._build_tools_spec = lambda log: None
    return entity, namespace


class ConversationResponseTests(unittest.IsolatedAsyncioTestCase):
    async def process(self, entity):
        log = SimpleNamespace(
            content=[SimpleNamespace(role="user", content="hello")],
            async_provide_llm_data=AsyncMock(),
        )
        log.async_add_assistant_content_without_tools = Mock(
            side_effect=log.content.append
        )
        user = SimpleNamespace(
            as_llm_context=lambda domain: None, extra_system_prompt=None
        )
        result = await entity._async_handle_message(user, log)
        log.async_add_assistant_content_without_tools.assert_called_once()
        return result

    async def test_api_failures_are_added_to_the_conversation(self):
        for response, error, expected in [
            ({"_http_status": 401}, None, "HTTP 401"),
            ({"_http_status": 400, "error": "invalid tools"}, None, "HTTP 400"),
            ({}, None, "Unexpected response format"),
            (None, asyncio.TimeoutError(), "Error talking"),
        ]:
            with self.subTest(expected=expected):
                entity, namespace = make_entity(response, error)
                result = await self.process(entity)
                self.assertIn(expected, result.content)
                namespace["_LOGGER"].error.assert_called_once()

    async def test_success_is_added_once(self):
        entity, namespace = make_entity({
            "choices": [{"message": {"content": "Hello!"}}]
        })
        result = await self.process(entity)
        self.assertEqual(result.content, "Hello!")
        namespace["_LOGGER"].error.assert_not_called()

    async def test_empty_response_has_an_explicit_error(self):
        entity, namespace = make_entity({
            "choices": [{"message": {"content": None}}]
        })
        result = await self.process(entity)
        self.assertEqual(result.content, "myAI returned an empty response.")


if __name__ == "__main__":
    unittest.main()
