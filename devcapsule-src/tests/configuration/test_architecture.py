"""Configuration dependencies must preserve the domain/adapter boundary."""
import ast
from pathlib import Path

from devcapsule import configuration
import pytest

pytestmark = pytest.mark.legacy


PACKAGE = "devcapsule.configuration"
ADAPTERS = {"storage", "execution", "operations", "history", "capability_commands", "capability_selection", "docker_arguments", "owner_commands", "derivation"}
CORE = {"file_formats", "manifest", "values", "bindings", "authorization", "nodes",
        "review", "fingerprints", "resolution", "freshness", "model", "capabilities", "manifest_document",
        "launcher_values", "listing", "home", "trust"}


def dependencies():
    """Include imports inside functions; moving a cycle there cannot hide it."""
    directory = Path(configuration.__file__).parent
    modules = {path.stem: path for path in directory.glob("*.py")}
    graph = {}
    for name, path in modules.items():
        imports = set()
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    parent = PACKAGE.split(".")[:len(PACKAGE.split(".")) - node.level + 1]
                    module = ".".join([*parent, *([node.module] if node.module else [])])
                else:
                    module = node.module or ""
                if module == PACKAGE:
                    imports.update(f"{PACKAGE}.{alias.name}" if alias.name in modules
                                   else f"{PACKAGE}.__init__" for alias in node.names)
                else:
                    imports.add(module)
        graph[f"{PACKAGE}.{name}"] = imports
    return graph


def test_configuration_dependencies_are_acyclic():
    graph = dependencies()
    completed = set()

    def visit(name, path):
        assert name not in path, "Configuration import cycle: " + " -> ".join((*path, name))
        if name in completed or name not in graph:
            return
        for dependency in sorted(graph[name]):
            visit(dependency, (*path, name))
        completed.add(name)

    for module in graph:
        visit(module, ())


def test_configuration_core_cannot_depend_on_effectful_adapters():
    graph = dependencies()
    forbidden = {f"{PACKAGE}.{name}" for name in ADAPTERS} | {
        "devcapsule.commands", "devcapsule.launch", "devcapsule.environment_realization",
        "devcapsule.materialization", "devcapsule.resolution_matrix",
    }
    for core in CORE:
        pending = [f"{PACKAGE}.{core}"]
        seen = set()
        while pending:
            module = pending.pop()
            if module in seen:
                continue
            seen.add(module)
            assert not any(module == target or module.startswith(target + ".") for target in forbidden), (
                f"Configuration core {core} depends on adapter {module}"
            )
            pending.extend(graph.get(module, ()))
