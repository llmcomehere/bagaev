"""Fixed helpers embedded by the L2 compiler; no expression interpreter."""


class L2RuntimeError(ValueError):
    def __init__(self, code, location):
        self.code = code
        self.location = dict(location)
        super().__init__(code)


class _Budget:
    def __init__(self):
        self.steps = 0


class _Frame:
    def __init__(self, budget, definition, pin, expression):
        self.budget = budget
        self.location = {"definition": definition, "pin": pin, "expression": expression}

    def require(self, condition, code="L2_TYPE"):
        if not condition:
            raise L2RuntimeError(code, self.location)

    def charge(self, amount=1):
        self.budget.steps += amount
        self.require(self.budget.steps <= 100000, "L2_BOUNDS")

    def boolean(self, value):
        self.require(type(value) is bool)
        return value

    def array(self, value):
        self.require(type(value) is list)
        self.require(len(value) <= 256, "L2_BOUNDS")
        return value

    def unicode(self, text):
        self.require(not any(0xD800 <= ord(c) <= 0xDFFF for c in text))

    def strings(self, values):
        self.require(all(type(v) is str for v in values))
        for value in values:
            self.unicode(value)
        for value in values:
            self.require(len(value.encode("utf-8")) <= 4096, "L2_BOUNDS")

    def key(self, value, previous):
        self.require(type(value) is list)
        self.require(1 <= len(value) <= 8 and
                     (previous is None or len(value) == len(previous)), "L2_BOUNDS")
        self.require(all(type(v) in (int, str) for v in value))
        if previous is not None:
            self.require(all(type(a) is type(b) for a, b in zip(value, previous)))
        for v in value:
            if type(v) is str:
                self.unicode(v)
        for v in value:
            self.require(-(1 << 63) <= v < (1 << 63) if type(v) is int else
                         len(v.encode("utf-8")) <= 4096, "L2_BOUNDS")
        return tuple(value)

    def update(self, base, fields):
        self.require(type(base) is dict)
        self.require(len(base) <= 32, "L2_BOUNDS")
        result = {**base, **fields}
        self.require(len(result) <= 32, "L2_BOUNDS")
        return result

    def get(self, value, key):
        self.require(type(value) is dict)
        self.require(key in value, "L2_FIELD")
        return value[key]

    def lt(self, a, b):
        self.require(type(a) in (int, str) and type(a) is type(b))
        if type(a) is str:
            self.strings((a, b))
        else:
            self.require(all(-(1 << 63) <= v < (1 << 63) for v in (a, b)), "L2_BOUNDS")
        return a < b

    def unique(self, value):
        self.array(value)
        self.strings(value)
        self.charge(len(value) ** 2)
        return list(dict.fromkeys(value))

    def sort(self, value):
        self.array(value)
        self.strings(value)
        self.charge(len(value) ** 2)
        return sorted(value)

    def increasing(self, value):
        self.array(value)
        self.strings(value)
        self.charge(len(value) ** 2)
        return all(a < b for a, b in zip(value, value[1:]))

    def string_size(self, value):
        self.require(type(value) is str)
        self.unicode(value)
        raw = len(value.encode("utf-8"))
        self.require(raw <= 4096, "L2_BOUNDS")
        return 2 + raw + sum(1 if c in '"\\\b\t\n\f\r' else 5 if ord(c) < 32
                            else 0 for c in value)

    def export(self, value):
        # Count occurrences, not unique objects: sharing must produce a new tree.
        result = [None]
        pending = [(value, result, 0, 1, frozenset())]
        count = size = 0
        while pending:
            item, destination, key, depth, parents = pending.pop()
            count += 1
            self.require(depth <= 64 and count <= 65536, "L2_BOUNDS")
            kind = type(item)
            self.require(kind in (dict, list, str, int, bool, type(None)))
            if kind in (dict, list):
                self.require(id(item) not in parents)
                self.require(len(item) <= (32 if kind is dict else 256), "L2_BOUNDS")
                lineage = parents | {id(item)}
                size += 2 + max(0, len(item) - 1)
                if kind is dict:
                    self.require(all(type(k) is str for k in item))
                    keys = sorted(item)
                    for field in keys:
                        size += self.string_size(field) + 1
                    target = {}
                    pending.extend((item[k], target, k, depth + 1, lineage)
                                   for k in reversed(keys))
                else:
                    target = [None] * len(item)
                    pending.extend((item[i], target, i, depth + 1, lineage)
                                   for i in range(len(item) - 1, -1, -1))
                destination[key] = target
            else:
                if kind is str:
                    size += self.string_size(item)
                elif kind is int:
                    self.require(-(1 << 63) <= item < (1 << 63), "L2_BOUNDS")
                    size += len(str(item))
                else:
                    size += 4 if item is None or item is True else 5
                destination[key] = item
            self.require(size <= 1048576, "L2_BOUNDS")
        return result[0]


def _drive(function, environment, budget):
    """Trampoline for generated calls; it never sees an L2 expression tree."""
    stack = [function(budget, environment, 1)]
    returned = None
    while stack:
        try:
            callee, bindings, depth = stack[-1].send(returned)
        except StopIteration as done:
            stack.pop()
            returned = done.value
        else:
            stack.append(callee(budget, bindings, depth))
            returned = None
    return returned
