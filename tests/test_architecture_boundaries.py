"""Bounded static review for the Airframe ownership boundary."""

import ast
import importlib.util
import re
import sys
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
AIRFRAME = ROOT / "docs" / "architecture" / "Airframe.md"
sys.path.insert(0, str(SRC))

from airframe_manifest import (  # noqa: E402
    ALLOWED_LAYER_DEPENDENCIES,
    CONFIGURATION,
    CORE,
    CORE_EXTERNAL_DEPENDENCIES,
    DECLARED_CONFIGURATION_CONSUMERS,
    MODULE_OWNERS,
    PRODUCT_ONLY_EXTERNAL_DEPENDENCIES,
    PRODUCT_SPECIFIC,
    SHARED,
)


PRODUCT_WORDS = frozenset({
    "academic",
    "atlas",
    "course",
    "curriculum",
    "msaib",
    "program",
    "radar",
    "semester",
    "student",
})
LEGACY_COLUMNS = ("academic_year", "program")
TEST_PRODUCT_TERMS = frozenset(
    {
        "beacon",
        "field-note",
        "field-notes",
        "field_note",
        "field_notes",
        "observation_kind",
    }
)


def module_name(path):
    parts = list(path.relative_to(SRC).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def source_modules():
    return {
        module_name(path): path
        for path in SRC.rglob("*.py")
        if "__pycache__" not in path.parts
    }


def documented_owners():
    inventory = AIRFRAME.read_text(encoding="utf-8").split(
        "## Runtime module inventory", 1
    )[1].split("## Static review automation", 1)[0]
    headings = {
        "### Wingman OS Core": CORE,
        "### Shared Product Framework": SHARED,
        "### Atlas-Specific": PRODUCT_SPECIFIC,
        "### Product Configuration": CONFIGURATION,
    }
    owner = None
    result = {}
    for line in inventory.splitlines():
        if line in headings:
            owner = headings[line]
        elif match := re.fullmatch(r"- `([^`]+)`", line):
            module = match.group(1)
            if owner is None or module in result:
                raise AssertionError(f"Invalid Airframe inventory row: {module}")
            result[module] = owner
    return result


def imports_from_source(importer, source, *, package=False):
    imports = set()
    package_name = importer if package else importer.rpartition(".")[0]
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if not node.level:
                if node.module:
                    imports.add(node.module)
                continue
            relative = "." * node.level + (node.module or "")
            resolved = importlib.util.resolve_name(relative, package_name)
            if node.module:
                imports.add(resolved)
            else:
                imports.update(
                    f"{resolved}.{alias.name}"
                    for alias in node.names
                    if alias.name != "*"
                )
    return imports


def imports_for(importer, path):
    return imports_from_source(
        importer,
        path.read_text(encoding="utf-8"),
        package=path.stem == "__init__",
    )


def local_dependency(import_name, owners):
    matches = [
        name
        for name in owners
        if import_name == name or import_name.startswith(f"{name}.")
    ]
    return max(matches, key=len) if matches else None


def dependency_violations(imports, owners):
    violations = []
    for importer, names in imports.items():
        allowed = ALLOWED_LAYER_DEPENDENCIES[owners[importer]]
        for name in names:
            dependency = local_dependency(name, owners)
            if dependency is not None and owners[dependency] not in allowed:
                violations.append((importer, dependency, owners[dependency]))
    return sorted(violations)


def migration_statement_identities(tree):
    tuples = {
        node.targets[0].id: node.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and isinstance(node.value, ast.Tuple)
    }
    identities = {}
    for node in ast.walk(tree):
        if (
            not isinstance(node, ast.Call)
            or not isinstance(node.func, ast.Name)
            or node.func.id != "Migration"
        ):
            continue
        keywords = {keyword.arg: keyword.value for keyword in node.keywords}
        version = keywords.get("version")
        statements = keywords.get("statements")
        if isinstance(statements, ast.Name):
            statements = tuples.get(statements.id)
        if (
            isinstance(version, ast.Constant)
            and isinstance(version.value, int)
            and isinstance(statements, ast.Tuple)
        ):
            for index, statement in enumerate(statements.elts):
                identities[id(statement)] = (
                    f"migration:{version.value}:statement:{index}"
                )
    return identities


def static_string(node):
    """Evaluate only bounded, side-effect-free static string forms."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = static_string(node.left), static_string(node.right)
        return left + right if left is not None and right is not None else None
    if isinstance(node, ast.FormattedValue):
        value = static_string(node.value)
        if (
            value is not None
            and node.conversion in {-1, ord("s")}
            and node.format_spec is None
        ):
            return value
        return None
    if isinstance(node, ast.JoinedStr):
        parts = [static_string(value) for value in node.values]
        return "".join(parts) if all(part is not None for part in parts) else None
    return None


def matched_words(value, identifier=False):
    if identifier:
        pieces = {
            part.lower()
            for part in re.split(
                r"[^a-zA-Z0-9]+|(?<=[a-z])(?=[A-Z])", value
            )
            if part
        }
        return PRODUCT_WORDS & pieces
    value = value.lower()
    return {
        word
        for word in PRODUCT_WORDS
        if re.search(rf"(?<![a-z0-9]){word}(?![a-z0-9])", value)
    }


def protected_identity(value, *, identifier=False):
    """Normalize vocabulary or physical SQL-column identity."""
    if not identifier:
        normalized = value.strip().lower()
        columns = re.findall(
            r"\b(?:academic_year|program)\b", normalized
        )
        sql_like = re.search(
            r"\b(?:select|insert|update|create\s+table|set)\b",
            normalized,
        )
        if columns and (
            normalized in LEGACY_COLUMNS or sql_like
        ):
            return "columns", tuple(sorted(columns))
    words = matched_words(value, identifier)
    return ("vocabulary", tuple(sorted(words))) if words else None


def dynamic_import_calls(source):
    """Find __import__ and importlib.import_module, including aliases."""
    tree = ast.parse(source)
    importlib_names = {"importlib"}
    import_module_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            importlib_names.update(
                alias.asname or alias.name
                for alias in node.names
                if alias.name == "importlib"
            )
        elif isinstance(node, ast.ImportFrom) and node.module == "importlib":
            import_module_names.update(
                alias.asname or alias.name
                for alias in node.names
                if alias.name == "import_module"
            )

    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and (
            node.func.id == "__import__"
            or node.func.id in import_module_names
        ):
            violations.append(node.func.id)
        elif (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "import_module"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in importlib_names
        ):
            violations.append(f"{node.func.value.id}.import_module")
    return violations


def product_identity_conditionals(source):
    """Find static product-ID behavior branches in ordinary Python."""
    tree = ast.parse(source)
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.If, ast.IfExp)):
            continue
        names = {
            value
            for child in ast.walk(node.test)
            for value in (
                getattr(child, "id", None),
                getattr(child, "attr", None),
            )
            if value in {"product_id", "product_key"}
        }
        static_values = {
            child.value
            for child in ast.walk(node.test)
            if (
                isinstance(child, ast.Constant)
                and isinstance(child.value, str)
            )
        }
        if names and static_values:
            violations.append(
                (node.lineno, tuple(sorted(static_values)))
            )
    return violations


def vocabulary_occurrences(module, source):
    tree = ast.parse(source)
    migration_identities = migration_statement_identities(tree)
    functions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    consumers = {}
    for function in functions:
        loaded_names = {
            node.id
            for node in ast.walk(function)
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
        }
        for name in loaded_names:
            consumers.setdefault(name, set()).add(function.name)
    parents = {
        id(child): parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }

    def context(node):
        binding = None
        while node is not None:
            if id(node) in migration_identities:
                return migration_identities[id(node)]
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return f"function:{node.name}"
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                names = [
                    target.id for target in targets if isinstance(target, ast.Name)
                ]
                if len(names) == 1:
                    named_consumers = sorted(consumers.get(names[0], ()))
                    binding = (
                        "functions:" + ",".join(named_consumers)
                        if named_consumers
                        else f"binding:{names[0]}"
                    )
            node = parents.get(id(node))
        return binding or "module"

    result = Counter()
    string_containers = (ast.BinOp, ast.FormattedValue, ast.JoinedStr)
    identifier_fields = ("id", "attr", "arg", "name", "asname")
    for node in ast.walk(tree):
        parent = parents.get(id(node))
        value = static_string(node)
        if value is not None and not (
            isinstance(parent, string_containers)
            and static_string(parent) is not None
        ):
            identity = protected_identity(value)
            if identity:
                result[(module, context(node), "string", identity)] += 1

        identifiers = [
            value
            for field in identifier_fields
            if isinstance((value := getattr(node, field, None)), str)
        ]
        if isinstance(node, ast.keyword) and node.arg:
            identifiers.append(node.arg)
        for identifier in identifiers:
            identity = protected_identity(identifier, identifier=True)
            if identity:
                result[(module, context(node), "identifier", identity)] += 1
    return result


LEGACY_CONSUMERS = (
    "functions:_legacy_source_values_from_metadata,"
    "_source_metadata_from_version_3_row"
)
ALLOWED_PRODUCT_VOCABULARY = Counter({
    (
        "ledger.migrations",
        "migration:1:statement:1",
        "string",
        ("columns", LEGACY_COLUMNS),
    ): 1,
    (
        "ledger.source_repository",
        LEGACY_CONSUMERS,
        "string",
        ("columns", ("program",)),
    ): 1,
    (
        "ledger.source_repository",
        LEGACY_CONSUMERS,
        "string",
        ("columns", ("academic_year",)),
    ): 1,
    **{
        (
            "ledger.source_repository",
            f"function:{function}",
            "string",
            ("columns", LEGACY_COLUMNS),
        ): 1
        for function in (
            "create_source",
            "get_source",
            "list_sources",
            "update_source",
        )
    },
})


class ArchitectureBoundaryTests(unittest.TestCase):
    def test_source_manifest_and_document_are_exact(self):
        self.assertEqual(set(source_modules()), set(MODULE_OWNERS))
        self.assertEqual(documented_owners(), MODULE_OWNERS)

    def test_local_imports_follow_dependency_direction(self):
        modules = source_modules()
        imports = {name: imports_for(name, path) for name, path in modules.items()}
        self.assertEqual(dependency_violations(imports, MODULE_OWNERS), [])

        relative = imports_from_source(
            "shared.framework", "from . import atlas_policy"
        )
        owners = {
            "shared.framework": SHARED,
            "shared.atlas_policy": PRODUCT_SPECIFIC,
        }
        self.assertEqual(
            dependency_violations(
                {
                    "shared.framework": relative,
                    "shared.atlas_policy": set(),
                },
                owners,
            ),
            [
                (
                    "shared.framework",
                    "shared.atlas_policy",
                    PRODUCT_SPECIFIC,
                )
            ],
        )

    def test_declared_consumers_and_external_dependencies(self):
        consumers = set()
        violations = []
        for importer, path in source_modules().items():
            imports = imports_for(importer, path)
            for name in imports:
                dependency = local_dependency(name, MODULE_OWNERS)
                if dependency and MODULE_OWNERS[dependency] == CONFIGURATION:
                    consumers.add(importer)
                root = name.split(".", 1)[0]
                if (
                    MODULE_OWNERS[importer] == CORE
                    and not dependency
                    and root not in sys.stdlib_module_names
                    and root not in CORE_EXTERNAL_DEPENDENCIES
                ):
                    violations.append((importer, root))
            roots = {name.split(".", 1)[0] for name in imports}
            for dependency, owner in PRODUCT_ONLY_EXTERNAL_DEPENDENCIES.items():
                if dependency in roots and MODULE_OWNERS[importer] != owner:
                    violations.append((importer, dependency))
        self.assertEqual(consumers, set(DECLARED_CONFIGURATION_CONSUMERS))
        self.assertEqual(violations, [])

    def test_core_and_shared_vocabulary_and_import_calls_are_exact(self):
        observed = Counter()
        dynamic_imports = {}
        for module, path in source_modules().items():
            if MODULE_OWNERS[module] not in {CORE, SHARED}:
                continue
            source = path.read_text(encoding="utf-8")
            observed.update(vocabulary_occurrences(module, source))
            calls = dynamic_import_calls(source)
            if calls:
                dynamic_imports[module] = calls
        self.assertEqual(observed, ALLOWED_PRODUCT_VOCABULARY)
        self.assertEqual(dynamic_imports, {})

    def test_core_and_shared_have_no_product_identity_conditionals(self):
        violations = {}
        for module, path in source_modules().items():
            if MODULE_OWNERS[module] not in {CORE, SHARED}:
                continue
            conditions = product_identity_conditionals(
                path.read_text(encoding="utf-8")
            )
            if conditions:
                violations[module] = conditions
        self.assertEqual(violations, {})

    def test_core_and_shared_have_no_test_product_vocabulary(self):
        violations = {}
        for module, path in source_modules().items():
            if MODULE_OWNERS[module] not in {CORE, SHARED}:
                continue
            source = path.read_text(encoding="utf-8").lower()
            matches = sorted(
                term
                for term in TEST_PRODUCT_TERMS
                if term in source
            )
            if matches:
                violations[module] = matches
        self.assertEqual(violations, {})

    def test_static_strings_identifiers_and_dynamic_imports_are_caught(self):
        sources = (
            'VALUE = "academic"\n',
            'VALUE = "aca" + "demic"\n',
            'VALUE = f"aca{\'demic\'}"\n',
        )
        occurrences = [
            vocabulary_occurrences("example", source) for source in sources
        ]
        self.assertEqual(occurrences[0], occurrences[1])
        self.assertEqual(occurrences[0], occurrences[2])
        identifiers = vocabulary_occurrences(
            "example", "def course_catalog():\n    return None\n"
        )
        self.assertTrue(any(key[2] == "identifier" for key in identifiers))

        constructed_imports = (
            "import importlib as loader\n"
            '__import__("query_" + "interpreter")\n'
            'loader.import_module(f"query_{\'interpreter\'}")\n'
        )
        self.assertEqual(
            dynamic_import_calls(constructed_imports),
            ["__import__", "loader.import_module"],
        )
        identity_branch = (
            "if context.product_id == 'example':\n"
            "    select_behavior()\n"
        )
        self.assertEqual(
            product_identity_conditionals(identity_branch),
            [(1, ("example",))],
        )

    def test_semantic_exception_identity_is_stable_and_exact(self):
        compact = (
            "def legacy_storage():\n"
            "    return 'SELECT program, academic_year FROM sources'\n"
        )
        reformatted = (
            "\n\n"
            "def legacy_storage():\n"
            "    return ('SELECT program, ' +\n"
            "            'academic_year FROM sources')\n"
        )
        expected = vocabulary_occurrences("ledger.source_repository", compact)
        self.assertEqual(
            expected,
            vocabulary_occurrences("ledger.source_repository", reformatted),
        )
        changed_sources = (
            (
                "ledger.source_repository",
                compact.replace("legacy_storage", "unapproved_storage"),
            ),
            ("other.module", compact),
            (
                "ledger.source_repository",
                compact.replace("academic_year", "academic"),
            ),
            (
                "ledger.source_repository",
                compact.replace("program,", "program, program,"),
            ),
        )
        for module, source in changed_sources:
            with self.subTest(module=module, source=source):
                self.assertNotEqual(
                    expected,
                    vocabulary_occurrences(module, source),
                )

        migration_source = (
            "SCHEMA = ('academic_year',)\n"
            "MIGRATIONS = (Migration("
            "version=1, name='initial', statements=SCHEMA),)\n"
        )
        migration = vocabulary_occurrences(
            "ledger.migrations", migration_source
        )
        self.assertEqual(
            {key[1] for key in migration},
            {"migration:1:statement:0"},
        )


if __name__ == "__main__":
    unittest.main()
