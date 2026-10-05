"""tools/*.py must parse on Python 3.11 (the user's machine). PEP 701 (Python 3.12) relaxed f-string syntax, so the code can pass on 3.12+
and still fail on 3.11 with a SyntaxError. This test finds those spots statically, on any Python.

On 3.12+ it tokenizes each file (an f-string is then FSTRING_START / FSTRING_MIDDLE / FSTRING_END plus ordinary tokens) and tracks which
tokens sit inside a replacement field `{...}` (and which are the format spec). In a field it flags what 3.11 rejects:
  - a backslash anywhere in the expression text, including inside a nested string or a line continuation;
  - a nested string or f-string that contains the enclosing f-string's quote (f-string with a double-quoted key inside a double-quoted f-string; inside a triple-quoted one only a triple quote counts);
  - a comment;
  - a newline in the expression of a single-quoted (non-triple) f-string.
On 3.11 and older the parser itself rejects these, so the test just compiles each file (the SyntaxError is the finding).

Limits: other 3.12-only syntax (PEP 695 `type X = ...` and generic `def f[T]`) is not checked on 3.12+; only 3.11 itself would reject it. A backslash in a format spec is allowed (3.11 accepts it); one inside an expression nested in a spec is flagged.
Not covered: a lambda or walrus colon at depth 0 inside a field is read as the start of the format spec (rare; the checks stay on, so
only the spec-versus-expression split could be off). The detector is exercised on small snippets below, because 3.11 is not installed here."""
import io
import sys
import tokenize
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent / "tools"
FILES = sorted(TOOLS.glob("*.py"))
HAS_PEP701 = sys.version_info >= (3, 12)


class _Ctx:
    """One open f-string: its quote and the open replacement fields (each 'expr' with a bracket depth, or 'spec')."""

    def __init__(self, delim, row):
        self.delim, self.row, self.frames = delim, row, []

    @property
    def in_expr(self):
        return bool(self.frames) and self.frames[-1][0] == "expr"


def _delim(text):
    body = text.lstrip("rRbBfFuU")
    return body[:3] if body[:3] in ('"""', "'''") else body[:1]


def find_violations(source):
    """[(line, message)] for 3.12-only f-string syntax in `source` (needs the 3.12+ tokenizer)."""
    out, stack, prev = [], [], None
    lines = source.splitlines()
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        t, s, row = tok.type, tok.string, tok.start[0]

        def flag(msg):
            out.append((row, msg))

        if t == tokenize.FSTRING_START:
            if stack and stack[-1].in_expr:
                _check_inside(stack, s, flag)
            stack.append(_Ctx(_delim(s), row))
            prev = tok
            continue
        if t == tokenize.FSTRING_END:
            ctx = stack.pop()
            if any(c.in_expr for c in stack):
                _check_inside(stack, s, flag)
            if stack and stack[-1].in_expr:
                _check_newline(stack, tok, flag)
            prev = tok
            continue
        if t == tokenize.FSTRING_MIDDLE:
            if any(c.in_expr for c in stack[:-1]):  # the literal or spec of an f-string that sits inside an outer expression
                _check_inside(stack[:-1], s, flag)
            prev = tok
            continue
        if not stack:
            prev = tok
            continue
        ctx = stack[-1]
        if not ctx.in_expr and not (ctx.frames and ctx.frames[-1][0] == "spec"):
            if t == tokenize.OP and s == "{":
                ctx.frames.append(["expr", 0])
            prev = tok
            continue
        if ctx.frames[-1][0] == "spec":  # inside a format spec: only a nested `{` or the closing `}` is a token
            if t == tokenize.OP and s == "{":
                ctx.frames.append(["expr", 0])
            elif t == tokenize.OP and s == "}":
                ctx.frames.pop()
            prev = tok
            continue
        # an ordinary token inside an expression
        if t == tokenize.COMMENT:
            flag("comment inside an f-string replacement field")
        elif t not in (tokenize.NL, tokenize.NEWLINE):
            _check_inside(stack, s, flag)
            _check_newline(stack, tok, flag)
        if prev is not None and prev.end[0] < row and prev.end[0] - 1 < len(lines) and "\\" in lines[prev.end[0] - 1][prev.end[1]:]:
            flag("backslash line continuation inside an f-string replacement field")
        frame = ctx.frames[-1]
        if t == tokenize.OP:
            if s in "([{":
                frame[1] += 1
            elif s in ")]}":
                if frame[1] > 0:
                    frame[1] -= 1
                else:
                    ctx.frames.pop()
            elif s == ":" and frame[1] == 0:
                frame[0] = "spec"
        prev = tok
    return out


def _check_inside(enclosing, text, flag):
    """`text` sits in an expression nested in the f-strings `enclosing` (outermost first)."""
    if "\\" in text:
        flag("backslash inside an f-string replacement field")
    for c in enclosing:
        if c.delim in text:
            flag(f"quote {c.delim} reused inside an f-string replacement field")
            break


def _check_newline(stack, tok, flag):
    ctx = stack[-1]
    if len(ctx.delim) == 1 and tok.start[0] > ctx.row:
        flag("newline inside the expression of a single-quoted f-string")


def violations_of(path):
    return find_violations(path.read_text(encoding="utf-8"))


# ---- the real files ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_tools_have_no_python_312_fstring_syntax(path):
    assert FILES, "no tools/*.py found"
    if not HAS_PEP701:
        compile(path.read_text(encoding="utf-8"), str(path), "exec")  # on 3.11 the parser rejects these forms itself
        return
    found = violations_of(path)
    assert not found, "; ".join(f"{path.name}:{ln}: {msg}" for ln, msg in found)


# ---- the detector itself (3.12+ only, because it needs the f-string tokens) -----------------------------------------
needs_312 = pytest.mark.skipif(not HAS_PEP701, reason="needs the PEP 701 tokenizer")

BAD = {
    "backslash": 'x = f"{"a\\n".join(v)}"\n',
    "backslash in plain expression": "x = f'{a}{b}'.format()\ny = f'{\"\\\\\".join(v)}'\n",
    "same quote": 'x = f"{d["k"]}"\n',
    "same quote single": "x = f'{d['k']}'\n",
    "triple reused": 'x = f"""{d["""k"""]}"""\n',
    "nested fstring same quote": 'x = f"{f"{a}"}"\n',
    "comment": 'x = f"""{a  # why\n}"""\n',
    "newline in single quoted": 'x = f"{a +\n b}"\n',
    "in a nested spec expression": 'x = f"{a:{"b"}}"\n',
}
GOOD = {
    "other quote": "x = f\"{d['k']}\"\n",
    "triple holds quotes": 'x = f"""{d["k"]} and {e[\'j\']}"""\n',
    "backslash in the literal": 'x = f"a\\n{b}\\t"\n',
    "doubled braces": 'x = f"{{not a field}} {a}"\n',
    "format spec": 'x = f"{a:>{w}} {b!r:10} {c:%Y-%m-%d}"\n',
    "dict and slice in a field": "x = f\"{ {1: 2}[1] } {s[1:2]}\"\n",
    "multi-line triple": 'x = f"""{a +\n b}"""\n',
    "nested other quote": "x = f\"{f'{a}'}\"\n",
    "plain strings are free": 'x = "a\\n" + \'it\\\'s\' + """q"""\n',
    "implicit concatenation": 'x = ("a" f"{b}"\n     f"{c}")\n',
}


@needs_312
@pytest.mark.parametrize("name", sorted(BAD))
def test_detector_flags_the_312_only_forms(name):
    assert find_violations(BAD[name]), BAD[name]


@needs_312
@pytest.mark.parametrize("name", sorted(GOOD))
def test_detector_passes_what_311_accepts(name):
    assert find_violations(GOOD[name]) == [], (GOOD[name], find_violations(GOOD[name]))
