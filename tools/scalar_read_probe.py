"""Observe immutable dialect class-field reads without replacing field values."""
import ast
import builtins
from collections import defaultdict
import functools
from pathlib import Path


def scalar_names(root):
    """Collect candidate names from class assignments in pristine dialect code."""
    names = set()
    for path in sorted((Path(root) / "sqlglot/dialects").glob("*.py")):
        tree = ast.parse(path.read_text())
        for owner in ast.walk(tree):
            if not isinstance(owner, ast.ClassDef):
                continue
            for statement in owner.body:
                if (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                        and isinstance(statement.targets[0], ast.Name)):
                    name, value = statement.targets[0].id, statement.value
                elif isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
                    name, value = statement.target.id, statement.value
                else:
                    continue
                if not name.isupper() or value is None:
                    continue
                try:
                    data = ast.literal_eval(value)
                except (ValueError, TypeError, SyntaxError, RecursionError):
                    continue
                if type(data) in (bool, int, str, float):
                    names.add(name)
    return names


class ScalarReadProbe:
    def __init__(self, names):
        self.names = names
        self.current = ""
        self.phase = ""
        self.uses = defaultdict(lambda: defaultdict(set))
        self.setup = defaultdict(set)
        self._installed_meta = False
        self._installed_instances = False

    def record(self, owner, name):
        if name not in self.names:
            return
        for base in owner.__mro__:
            if base.__module__ == "sqlglot" or base.__module__.startswith("sqlglot."):
                key = base.__module__ + ":" + base.__qualname__
                self.uses[key][name].add(self.current)
                if self.phase == "setup" and self.current:
                    self.setup[(key, name)].add(self.current.rsplit("::", 1)[0])

    def wrap_meta(self, meta):
        if self._installed_meta:
            return
        original = meta.__dict__.get("__getattribute__", type.__getattribute__)

        @functools.wraps(original)
        def wrapped(owner, name):
            value = original(owner, name)
            if name in self.names:
                self.record(owner, name)
            return value

        meta.__getattribute__ = wrapped
        self._installed_meta = True

    def wrap_instances(self, base):
        if self._installed_instances:
            return
        original = base.__dict__.get("__getattribute__", object.__getattribute__)

        @functools.wraps(original)
        def wrapped(instance, name):
            value = original(instance, name)
            if name in self.names:
                self.record(type(instance), name)
            return value

        base.__getattribute__ = wrapped
        self._installed_instances = True

    def install_early(self):
        original = builtins.__build_class__

        def build(function, name, *bases, **kwargs):
            result = original(function, name, *bases, **kwargs)
            if result.__module__ == "sqlglot.dialects.dialect" and name == "_Dialect":
                self.wrap_meta(result)
            elif result.__module__ == "sqlglot.dialects.dialect" and name == "Dialect":
                self.wrap_instances(result)
            return result

        builtins.__build_class__ = build
        return original

    def install_direct(self):
        from sqlglot.dialects.dialect import _Dialect, Dialect
        self.wrap_meta(_Dialect)
        self.wrap_instances(Dialect)

    def payload(self):
        return {owner: {name: sorted(ids) for name, ids in sorted(fields.items())}
                for owner, fields in sorted(self.uses.items())}
