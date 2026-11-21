"""Observe actual numeric escape tuple consumption on pristine SQLGlot.

Only method calls that retrieve an existing key are recorded. The dictionary
object from Tokenizer._init_core identifies all owner classes that might be
affected by a changed inherited NUMERIC_ESCAPES field.
"""
import builtins
from collections import defaultdict
import functools


class NumericKeyProbe:
    def __init__(self):
        self.current = ""
        self.phase = ""
        self.owners = defaultdict(set)
        self.objects = {}
        self.uses = defaultdict(lambda: defaultdict(set))
        self.setup = defaultdict(set)

    @staticmethod
    def keys(instance):
        return [base.__module__ + ":" + base.__qualname__
                for base in type(instance).__mro__
                if base.__module__ == "sqlglot" or base.__module__.startswith("sqlglot.")]

    def wrap_tokenizer(self, base):
        method = base.__dict__.get("_init_core")
        if method is None or getattr(method, "_blast_numeric_key_probe", False):
            return

        @functools.wraps(method)
        def wrapped(instance):
            core = method(instance)
            table = instance.NUMERIC_ESCAPES
            self.objects[id(table)] = table
            self.owners[id(table)].update(self.keys(instance))
            return core

        wrapped._blast_numeric_key_probe = True
        base._init_core = wrapped

    def wrap_core(self, base):
        from sqlglot.tokenizer_core import _OCTAL_CHARS

        for name in ("_scan_numeric_escape", "_read_byte_escape"):
            method = base.__dict__[name]
            if getattr(method, "_blast_numeric_key_probe", False):
                continue

            @functools.wraps(method)
            def wrapped(instance, *args, __method=method, __name=name):
                if __name == "_scan_numeric_escape":
                    peek = instance._peek
                else:
                    peek = instance.sql[args[0] + 1: args[0] + 2]
                key = "0" if peek in _OCTAL_CHARS else peek
                if key in instance.numeric_escapes:
                    for owner in self.owners.get(id(instance.numeric_escapes), ()):
                        self.uses[owner][key].add(self.current)
                        if self.phase == "setup" and self.current:
                            self.setup[(owner, key)].add(self.current.rsplit("::", 1)[0])
                return __method(instance, *args)

            wrapped._blast_numeric_key_probe = True
            setattr(base, name, wrapped)

    def install_early(self):
        original = builtins.__build_class__

        def build(function, name, *bases, **kwargs):
            result = original(function, name, *bases, **kwargs)
            if result.__module__ == "sqlglot.tokens" and name == "Tokenizer":
                self.wrap_tokenizer(result)
            elif result.__module__ == "sqlglot.tokenizer_core" and name == "TokenizerCore":
                self.wrap_core(result)
            return result

        builtins.__build_class__ = build
        return original

    def install_direct(self):
        from sqlglot.tokens import Tokenizer
        from sqlglot.tokenizer_core import TokenizerCore
        self.wrap_tokenizer(Tokenizer)
        self.wrap_core(TokenizerCore)

    def payload(self):
        return {owner: {key: sorted(ids) for key, ids in sorted(keys.items())}
                for owner, keys in sorted(self.uses.items())}
