"""PromptTemplateLoader tests."""
from __future__ import annotations
import pytest
from pydantic import BaseModel
from infrastructure.ai.prompt_template_loader import PromptTemplateLoader


@pytest.fixture(autouse=True)
def _reset_singleton():
    PromptTemplateLoader.reset_instance()
    yield
    PromptTemplateLoader.reset_instance()


@pytest.fixture
def builtin_loader():
    return PromptTemplateLoader.get_instance()


class TestRender:
    def test_render_static(self, builtin_loader):
        result = builtin_loader.render("llm_default", "system")
        assert "小说创作助手" in result

    def test_render_with_variable(self, builtin_loader):
        result = builtin_loader.render("tension_scoring", "system", prev_tension="75")
        assert "75/100" in result

    def test_render_missing_raises_keyerror(self, builtin_loader):
        with pytest.raises(KeyError):
            builtin_loader.render("nonexistent_xyz", "system")


class TestFallback:
    def test_fallback_used_when_missing(self, builtin_loader):
        result = builtin_loader.render_with_fallback(
            "nonexistent_xyz", "system",
            fallback="Hello {{ name }}",
            name="World",
        )
        assert result == "Hello World"

    def test_file_takes_priority(self, builtin_loader):
        result = builtin_loader.render_with_fallback(
            "llm_default", "system", fallback="FALLBACK"
        )
        assert "FALLBACK" not in result


class TestRenderToPrompt:
    def test_returns_prompt(self, builtin_loader):
        from domain.ai.value_objects.prompt import Prompt
        prompt = builtin_loader.render_to_prompt(
            "tension_scoring",
            system_vars={"prev_tension": "50"},
            user_vars={"chapter_number": 5, "body": "test"},
            fallback_system="FB",
            fallback_user="FB",
        )
        assert isinstance(prompt, Prompt)
        assert "50/100" in prompt.system


class TestContracts:
    def test_contract_for_json_node(self, builtin_loader):
        contract = builtin_loader.get_contract_for("tension_scoring")
        assert contract is not None
        assert issubclass(contract, BaseModel)

    def test_contract_for_text_node_is_none(self, builtin_loader):
        assert builtin_loader.get_contract_for("ai_generation") is None

    def test_response_format(self, builtin_loader):
        fmt = builtin_loader.get_response_format_for("tension_scoring")
        assert fmt is not None
        assert fmt["type"] == "json_schema"


class TestSingleton:
    def test_same_instance(self):
        l1 = PromptTemplateLoader.get_instance()
        l2 = PromptTemplateLoader.get_instance()
        assert l1 is l2


class TestIdempotent:
    def test_same_input_same_output(self, builtin_loader):
        r1 = builtin_loader.render_to_prompt(
            "tension_scoring",
            system_vars={"prev_tension": "50"},
            user_vars={"chapter_number": 1, "body": "test"},
            fallback_system="FB", fallback_user="FB",
        )
        r2 = builtin_loader.render_to_prompt(
            "tension_scoring",
            system_vars={"prev_tension": "50"},
            user_vars={"chapter_number": 1, "body": "test"},
            fallback_system="FB", fallback_user="FB",
        )
        assert r1.system == r2.system
        assert r1.user == r2.user


class TestTemplateSyntax:
    def test_all_system_compile(self, builtin_loader):
        errors = []
        for node in builtin_loader.list_nodes():
            try:
                builtin_loader.render(node, "system")
            except KeyError:
                pass
            except Exception as e:
                errors.append(f"{node}/system: {e}")
        assert not errors

    def test_all_user_compile(self, builtin_loader):
        errors = []
        for node in builtin_loader.list_nodes():
            try:
                builtin_loader.render(node, "user")
            except KeyError:
                pass
            except Exception as e:
                errors.append(f"{node}/user: {e}")
        assert not errors


class TestNodes:
    def test_list_nodes(self, builtin_loader):
        nodes = builtin_loader.list_nodes()
        assert len(nodes) >= 16
        assert "tension_scoring" in nodes

    def test_json_nodes_subset(self, builtin_loader):
        json_nodes = builtin_loader.list_json_nodes()
        assert "tension_scoring" in json_nodes
        assert "ai_generation" not in json_nodes
