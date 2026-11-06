"""Bounded, deterministic calculations. No submitted source code is executed."""

import ast
import math
import re
from collections import Counter
from functools import reduce
from itertools import product

import sympy as sp


class ToolError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code, self.message = code, message

    def to_dict(self):
        return {"error": {"code": self.code, "message": self.message}}


def _fail(message, code="invalid_arguments"):
    raise ToolError(code, message)


def _text(value, label, maximum):
    if not isinstance(value, str) or not value or len(value) > maximum:
        _fail(f"{label} must be a nonempty string of at most {maximum} characters.")
    return value


def _fields(args, required, optional=()):
    if set(args) - {"operation", *required, *optional} or any(k not in args for k in required):
        _fail(f"Expected fields: operation, {', '.join(required)}; optional: {', '.join(optional) or 'none'}.")


def _number(value, label, positive=False, nonnegative=False):
    if type(value) not in (int, float) or not math.isfinite(value) or (value and not 1e-100 <= abs(value) <= 1e100):
        _fail(f"{label} must be zero or finite with magnitude between 1e-100 and 1e100.")
    if (positive and value <= 0) or (nonnegative and value < 0):
        _fail(f"{label} must be {'positive' if positive else 'nonnegative'}.")
    return value


_SYMBOLS = {name: sp.Symbol(name, real=True) for name in ("x", "y", "z", "t")}
_FUNCTIONS = {"sin": (sp.sin, math.sin), "cos": (sp.cos, math.cos),
              "tan": (sp.tan, math.tan), "sqrt": (sp.sqrt, math.sqrt),
              "exp": (sp.exp, math.exp), "log": (sp.log, math.log),
              "Abs": (sp.Abs, abs)}


def _expression(source):
    source = _text(source, "expression", 256)
    try:
        tree = ast.parse(source, mode="eval")
    except (SyntaxError, ValueError, RecursionError):
        _fail("Invalid expression syntax.")
    if sum(1 for _ in ast.walk(tree)) > 80:
        _fail("Expression exceeds 80 syntax nodes.")

    def numeric(expr):
        if expr.free_symbols:
            return None
        value = float(expr)
        if not math.isfinite(value) or (value and not 1e-100 <= abs(value) <= 1e100) or (value == 0 and expr != 0):
            _fail("Numeric intermediate exceeds the supported magnitude range.")
        return value

    def build(node, depth=0):
        if depth > 16:
            _fail("Expression nesting exceeds 16 levels.")
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            raw = ast.get_source_segment(source, node)
            if len(raw) > 32 or not re.fullmatch(r"(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", raw):
                _fail("Use decimal numeric literals of at most 32 characters.")
            if not math.isfinite(node.value) or (node.value and not 1e-100 <= abs(node.value) <= 1e12):
                _fail("Numeric literals must have magnitude between 1e-100 and 1e12, or be zero.")
            if "e" in raw.lower() and abs(int(raw.lower().split("e")[1])) > 100:
                _fail("Literal exponent exceeds 100.")
            expr = sp.Rational(raw)
        elif isinstance(node, ast.Name) and node.id in {**_SYMBOLS, "pi": sp.pi, "E": sp.E}:
            expr = {**_SYMBOLS, "pi": sp.pi, "E": sp.E}[node.id]
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            expr = build(node.operand, depth + 1)
            if isinstance(node.op, ast.USub):
                expr = -expr
        elif isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)):
            left, right = build(node.left, depth + 1), build(node.right, depth + 1)
            a, b = numeric(left), numeric(right)
            if isinstance(node.op, ast.Pow):
                if not right.is_Integer or not -10 <= right <= 10:
                    _fail("Powers require an integer exponent from -10 to 10.")
                if any(max(abs(int(atom.p)).bit_length(), int(atom.q).bit_length()) * abs(int(right)) > 1024 for atom in left.atoms(sp.Rational)):
                    _fail("Power exceeds the exact arithmetic size limit.")
                if a is not None and b is not None:
                    numeric(sp.Float(math.pow(a, b)))
                expr = left ** right
            elif isinstance(node.op, ast.Div):
                if right.is_zero:
                    _fail("Division by zero is undefined.")
                expr = left / right
            elif isinstance(node.op, ast.Mult):
                expr = left * right
            elif isinstance(node.op, ast.Sub):
                expr = left - right
            else:
                expr = left + right
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCTIONS and len(node.args) == 1 and not node.keywords:
            arg = build(node.args[0], depth + 1)
            value = numeric(arg)
            if value is not None:
                if node.func.id == "exp" and abs(value) > 100:
                    _fail("Numeric exp arguments must have magnitude at most 100.")
                _FUNCTIONS[node.func.id][1](value)  # Check the real-valued domain first.
            expr = _FUNCTIONS[node.func.id][0](arg)
        else:
            _fail("Unsupported expression syntax, symbol, or function.")
        if expr.is_finite is False or expr.is_real is False:
            _fail("Only finite, real-valued intermediate expressions are supported.")
        if any(max(abs(int(atom.p)).bit_length(), int(atom.q).bit_length()) > 1024 for atom in expr.atoms(sp.Rational)):
            _fail("Expression exceeds the exact arithmetic size limit.")
        numeric(expr)
        return expr

    try:
        return build(tree.body)
    except ToolError:
        raise
    except (ValueError, TypeError, OverflowError, ZeroDivisionError, RecursionError):
        _fail("Expression is outside the supported real-valued arithmetic limits.")


def _polynomial_degree(expr, symbol, limit):
    """Bound degree without expanding powers or constructing a dense polynomial."""
    if symbol not in expr.free_symbols:
        degree = 0
    elif expr == symbol:
        degree = 1
    elif expr.is_Add:
        degree = max(_polynomial_degree(term, symbol, limit) for term in expr.args)
    elif expr.is_Mul:
        degree = sum(_polynomial_degree(term, symbol, limit) for term in expr.args)
    elif expr.is_Pow and expr.exp.is_Integer and expr.exp >= 0:
        degree = _polynomial_degree(expr.base, symbol, limit) * int(expr.exp)
    else:
        _fail("Integration and solving support one-variable polynomials only.", "unsupported")
    if degree > limit:
        _fail(f"Operation supports polynomial degree at most {limit}.", "unsupported")
    return degree


def _math(operation, args):
    _fields(args, ("expression",), ("variable",))
    variable = args.get("variable", "x")
    if not isinstance(variable, str) or variable not in _SYMBOLS:
        _fail("variable must be x, y, z, or t.")
    expr, symbol = _expression(args["expression"]), _SYMBOLS[variable]
    assumptions = ["Real variables; expressions apply where all terms are real and defined; derivatives exclude singularities. Bounded arithmetic and allowlisted syntax."]
    if operation == "evaluate":
        if expr.free_symbols:
            _fail("Evaluation requires an expression without unresolved variables.")
        result = {"exact": str(expr), "decimal": str(expr.evalf(15))}
    elif operation == "differentiate":
        result = {"expression": str(sp.diff(expr, symbol)), "variable": variable}
    elif operation in ("integrate", "solve"):
        if expr.free_symbols - {symbol}:
            _fail("Integration and solving support one-variable polynomials only.", "unsupported")
        _polynomial_degree(expr, symbol, 12 if operation == "integrate" else 4)
        poly = sp.Poly(expr, symbol)
        if any(not c.is_Rational or max(abs(int(c.p)).bit_length(), int(c.q).bit_length()) > 256 for c in poly.coeffs()):
            _fail("Polynomial coefficients must be rational numbers of at most 256 bits.", "unsupported")
        if operation == "integrate":
            if poly.degree() > 12:
                _fail("Integration supports polynomial degree at most 12.", "unsupported")
            result = {"expression": str(poly.integrate().as_expr()) + " + C", "variable": variable}
        else:
            if poly.is_zero or poly.degree() > 4:
                _fail("Solving requires a nonzero polynomial of degree at most four.", "unsupported")
            roots = poly.all_roots(radicals=False)
            result = {"roots": [str(r) for r in roots], "decimal_roots": [str(r.evalf(15)) for r in roots]}
            assumptions.append("Expression is set equal to zero; polynomial roots are reported over the complex numbers and include multiplicity.")
    else:
        _fail("Unknown math operation.", "unknown_operation")
    return result, assumptions


def _physics(operation, args):
    specs = {"force": (("mass_kg", "acceleration_m_s2"), "N", "F = m * a"),
             "kinetic_energy": (("mass_kg", "speed_m_s"), "J", "K = 0.5 * m * v^2"),
             "ideal_gas_pressure": (("moles", "temperature_k", "volume_m3"), "Pa", "P = n * R * T / V")}
    if operation not in specs:
        _fail("Unknown physics operation.", "unknown_operation")
    fields, unit, formula = specs[operation]
    _fields(args, fields)
    values = [_number(args[k], k, positive=operation == "ideal_gas_pressure", nonnegative=k in ("mass_kg", "speed_m_s")) for k in fields]
    if operation == "force":
        value, assumptions = values[0] * values[1], ["Classical mechanics; constant inertial mass; acceleration is signed along one axis."]
    elif operation == "kinetic_energy":
        if values[1] > 2997924.58:
            _fail("Classical kinetic energy supports speeds at most 1% of light speed (2997924.58 m/s).", "unsupported")
        value, assumptions = 0.5 * values[0] * values[1] ** 2, ["Classical translational kinetic energy; speeds much lower than light speed."]
    else:
        value, assumptions = values[0] * 8.31446261815324 * values[1] / values[2], ["Ideal gas model in equilibrium; R = 8.31446261815324 J/(mol K)."]
    _number(value, "result")
    return {"value": value, "unit": unit, "formula": formula}, assumptions


_ELEMENTS = set("H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og".split())


def _formula(formula):
    if not formula or len(formula) > 80:
        _fail("Each formula must contain 1 to 80 characters.")
    tokens = re.findall(r"[A-Z][a-z]?|\d+|[()]", formula)
    if "".join(tokens) != formula:
        _fail("Use neutral formulas with element symbols and parentheses; charges and hydrates are unsupported.", "unsupported")
    index = 0

    def group(depth=0):
        nonlocal index
        if depth > 4:
            _fail("Formula parentheses exceed four levels.")
        counts = Counter()
        while index < len(tokens) and tokens[index] != ")":
            token = tokens[index]
            index += 1
            if token == "(":
                part = group(depth + 1)
                if index >= len(tokens) or tokens[index] != ")":
                    _fail("Unmatched formula parenthesis.")
                index += 1
            elif token in _ELEMENTS:
                part = Counter({token: 1})
            else:
                _fail("Unknown element or misplaced count in formula.")
            multiplier = 1
            if index < len(tokens) and tokens[index].isdigit():
                multiplier = int(tokens[index])
                index += 1
                if not 1 <= multiplier <= 1000:
                    _fail("Formula counts must be between 1 and 1000.")
            counts.update({k: v * multiplier for k, v in part.items()})
            if sum(counts.values()) > 10000:
                _fail("Formula exceeds 10000 atoms.")
        if not counts:
            _fail("Empty formula group.")
        return counts

    counts = group()
    if index != len(tokens):
        _fail("Unmatched formula parenthesis.")
    return counts


def _chemistry(operation, args):
    if operation != "balance":
        _fail("Unknown chemistry operation.", "unknown_operation")
    _fields(args, ("reaction",))
    reaction = _text(args["reaction"], "reaction", 512)
    sides = reaction.split("->")
    if len(sides) != 2:
        _fail("Reaction must contain one '->' between reactants and products.")
    left, right = ([item.strip() for item in side.split("+")] for side in sides)
    if not 2 <= len(left) + len(right) <= 12:
        _fail("A reaction must contain 2 to 12 species.")
    formulas = left + right
    counts = [_formula(item) for item in formulas]
    elements = sorted(set().union(*(set(c) for c in counts)))
    matrix = sp.Matrix([[c.get(e, 0) * (1 if i < len(left) else -1) for i, c in enumerate(counts)] for e in elements])
    basis = matrix.nullspace()
    if len(basis) != 1:
        _fail("Reaction has no unique balance up to overall scale.", "unsupported")
    vector = basis[0]
    scale = sp.ilcm(*(v.q for v in vector))
    coefficients = [int(v * scale) for v in vector]
    divisor = reduce(math.gcd, coefficients)
    coefficients = [v // divisor for v in coefficients]
    if coefficients[0] < 0:
        coefficients = [-v for v in coefficients]
    if any(v <= 0 or v > 10000 for v in coefficients):
        _fail("No supported balance with all positive coefficients at most 10000.", "unsupported")
    rendered = [f"{n} {formula}" if n != 1 else formula for n, formula in zip(coefficients, formulas)]
    return {"reaction": " + ".join(rendered[:len(left)]) + " -> " + " + ".join(rendered[len(left):]), "coefficients": coefficients}, ["Neutral species; element conservation only. Balance does not establish reaction feasibility or conditions."]


_CODONS = dict(zip(("".join(c) for c in product("TCAG", repeat=3)), "FFLLSSSSYY**CC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG"))


def _biology(operation, args):
    _fields(args, ("sequence",), ("kind",))
    sequence = "".join(_text(args["sequence"], "sequence", 40000).split()).upper()
    kind = args.get("kind", "DNA")
    if kind not in ("DNA", "RNA") or not sequence or len(sequence) > 30000 or set(sequence) - set("ACGT" if kind == "DNA" else "ACGU"):
        _fail("Use 1 to 30000 unambiguous DNA (ACGT) or RNA (ACGU) bases and kind DNA or RNA.")
    assumptions = ["Unambiguous bases only; whitespace ignored; no medical or diagnostic inference."]
    if operation == "statistics":
        result = {"kind": kind, "length": len(sequence), "counts": {b: sequence.count(b) for b in ("ACGT" if kind == "DNA" else "ACGU")}, "gc_percent": 100 * (sequence.count("G") + sequence.count("C")) / len(sequence)}
    elif operation == "translate":
        if len(sequence) % 3:
            _fail("Translation requires a sequence length divisible by three.")
        dna = sequence.replace("U", "T")
        result = {"protein": "".join(_CODONS[dna[i:i + 3]] for i in range(0, len(dna), 3))}
        assumptions.append("Standard nuclear genetic code; forward strand, reading frame starts at first base; '*' marks stop; no splicing or start-codon requirement.")
    else:
        _fail("Unknown biology operation.", "unknown_operation")
    return result, assumptions


def _computers(operation, args):
    if operation != "inspect":
        _fail("Unknown computers operation.", "unknown_operation")
    _fields(args, ("source",))
    source = _text(args["source"], "source", 20000)
    assumptions = ["Python AST parsing and structure only; contextual compiler errors may remain. Submitted code is never executed; no behavior or security guarantee."]
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return {"ast_parse_valid": False, "message": exc.msg, "line": exc.lineno}, assumptions
    except (ValueError, RecursionError):
        _fail("Source exceeds parser limits or contains invalid characters.")
    nodes = list(ast.walk(tree))
    if len(nodes) > 4000:
        _fail("Source exceeds 4000 syntax nodes.")
    return {"ast_parse_valid": True, "node_count": len(nodes), "functions": [n.name for n in nodes if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))], "classes": [n.name for n in nodes if isinstance(n, ast.ClassDef)], "import_statements": sum(isinstance(n, (ast.Import, ast.ImportFrom)) for n in nodes)}, assumptions


def run_tool(name, arguments):
    """Return JSON-safe evidence, or raise ToolError with a stable error code."""
    handlers = {"math": _math, "physics": _physics, "chemistry": _chemistry, "biology": _biology, "computers": _computers}
    if not isinstance(name, str) or name not in handlers:
        _fail("Unknown tool; choose math, physics, chemistry, biology, or computers.", "unknown_tool")
    if not isinstance(arguments, dict) or any(not isinstance(k, str) for k in arguments):
        _fail("arguments must be an object with string keys.")
    operation = _text(arguments.get("operation"), "operation", 32)
    try:
        result, assumptions = handlers[name](operation, arguments)
    except (OverflowError, ZeroDivisionError):
        _fail("Calculation exceeds supported numeric limits.")
    return {"verified": True, "domain": name, "operation": operation, "result": result, "assumptions": assumptions}
