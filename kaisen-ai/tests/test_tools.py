import json
import unittest
from unittest.mock import patch

from kaisen.tools import ToolError, run_tool


class ToolsTests(unittest.TestCase):
    def test_exact_arithmetic_and_decimal_literal(self):
        result = run_tool("math", {"operation": "evaluate", "expression": "0.123456789123456789 + 1/3"})
        self.assertEqual(result["result"]["exact"], "1370370367370370367/3000000000000000000")
        self.assertTrue(result["verified"])
        json.dumps(result, allow_nan=False)

    def test_differentiate_integrate_and_solve(self):
        self.assertEqual(run_tool("math", {"operation": "differentiate", "expression": "sin(x) + x**3"})["result"]["expression"], "3*x**2 + cos(x)")
        self.assertEqual(run_tool("math", {"operation": "integrate", "expression": "3*x**2"})["result"]["expression"], "x**3 + C")
        self.assertEqual(run_tool("math", {"operation": "solve", "expression": "x**2 - 1"})["result"]["roots"], ["-1", "1"])

    def test_nonpolynomial_and_ambiguous_math_are_explicitly_unsupported(self):
        for operation, expression in [("integrate", "sin(x)"), ("solve", "x-x"), ("solve", "x**5-1")]:
            with self.subTest(operation=operation, expression=expression), self.assertRaises(ToolError) as raised:
                run_tool("math", {"operation": operation, "expression": expression})
            self.assertEqual(raised.exception.code, "unsupported")

    def test_malicious_math_never_executes(self):
        payloads = ["__import__('os').system('id')", "().__class__.__bases__", "[x for x in (1,2)]", "sin(x, **{})", "lambda: 1", "True", "x[0]"]
        with patch("os.system", side_effect=AssertionError("must not execute")):
            for expression in payloads:
                with self.subTest(expression=expression), self.assertRaises(ToolError):
                    run_tool("math", {"operation": "evaluate", "expression": expression})

    def test_math_numeric_bounds_and_domains(self):
        for expression in ["1e309", "1e-999", "exp(exp(100))", "((999999999999**10)**10)**10", "((1000000000000*x)**10)**10", "1/0", "sqrt(-1)", "tan(pi/2)", "log(0)"]:
            with self.subTest(expression=expression), self.assertRaises(ToolError):
                run_tool("math", {"operation": "evaluate", "expression": expression})

    def test_polynomial_degree_is_bounded_before_expansion(self):
        for operation in ("integrate", "solve"):
            for expression in ["((x**10)**10)**10", "(((x+1)**10+1)**10+1)**10"]:
                with self.subTest(operation=operation, expression=expression), self.assertRaises(ToolError) as raised:
                    run_tool("math", {"operation": operation, "expression": expression})
                self.assertEqual(raised.exception.code, "unsupported")

    def test_physics_units_and_values(self):
        self.assertEqual(run_tool("physics", {"operation": "force", "mass_kg": 2, "acceleration_m_s2": -3})["result"]["value"], -6)
        kinetic = run_tool("physics", {"operation": "kinetic_energy", "mass_kg": 2, "speed_m_s": 3})["result"]
        self.assertEqual((kinetic["value"], kinetic["unit"]), (9, "J"))
        pressure = run_tool("physics", {"operation": "ideal_gas_pressure", "moles": 1, "temperature_k": 300, "volume_m3": 0.024})["result"]
        self.assertAlmostEqual(pressure["value"], 103930.7827269155)

    def test_physics_rejects_invalid_inputs(self):
        for values in [{"moles": 1, "temperature_k": -1, "volume_m3": 1}, {"moles": True, "temperature_k": 300, "volume_m3": 1}, {"moles": 1, "temperature_k": 300, "volume_m3": 0}, {"moles": 1e-300, "temperature_k": 1e-300, "volume_m3": 1}]:
            with self.subTest(values=values), self.assertRaises(ToolError):
                run_tool("physics", {"operation": "ideal_gas_pressure", **values})
        with self.assertRaises(ToolError):
            run_tool("physics", {"operation": "kinetic_energy", "mass_kg": 1, "speed_m_s": 1e9})

    def test_balances_element_counts_and_parentheses(self):
        for reaction, expected in [("H2 + O2 -> H2O", [2, 1, 2]), ("Ca(OH)2 + HCl -> CaCl2 + H2O", [1, 2, 1, 2]), ("C2H6 + O2 -> CO2 + H2O", [2, 7, 4, 6])]:
            with self.subTest(reaction=reaction):
                result = run_tool("chemistry", {"operation": "balance", "reaction": reaction})
                self.assertEqual(result["result"]["coefficients"], expected)
                self.assertIn("feasibility", result["assumptions"][0])

    def test_malformed_unsupported_and_ambiguous_chemistry(self):
        for reaction in ["H0 + O2 -> H2O", "Xx2 -> H2", "Ca(OH2 -> CaO + H2", "H2 + O2 -> H2O + H2O2", "Fe2+ -> Fe3+", "CuSO4.5H2O -> CuSO4 + H2O", "H2 -> O2", "2H2 + O2 -> H2O", "H() -> H"]:
            with self.subTest(reaction=reaction), self.assertRaises(ToolError):
                run_tool("chemistry", {"operation": "balance", "reaction": reaction})

    def test_dna_and_rna_statistics(self):
        result = run_tool("biology", {"operation": "statistics", "sequence": "ac gt\nGC"})["result"]
        self.assertEqual(result["counts"], {"A": 1, "C": 2, "G": 2, "T": 1})
        self.assertAlmostEqual(result["gc_percent"], 200 / 3)
        self.assertEqual(run_tool("biology", {"operation": "statistics", "sequence": "ACGU", "kind": "RNA"})["result"]["counts"]["U"], 1)

    def test_translation_standard_code_and_stop(self):
        for kind, sequence in [("DNA", "ATGTTTTAA"), ("RNA", "AUGUUUUAA")]:
            self.assertEqual(run_tool("biology", {"operation": "translate", "kind": kind, "sequence": sequence})["result"]["protein"], "MF*")

    def test_biology_invalid_alphabet_and_frame(self):
        for sequence, kind, operation in [("ACGU", "DNA", "statistics"), ("ACGT", "RNA", "statistics"), ("NNN", "DNA", "translate"), ("AT", "DNA", "translate"), ("  ", "DNA", "statistics")]:
            with self.subTest(sequence=sequence), self.assertRaises(ToolError):
                run_tool("biology", {"operation": operation, "kind": kind, "sequence": sequence})

    def test_python_inspection_never_executes_code(self):
        with patch("os.system", side_effect=AssertionError("must not execute")):
            result = run_tool("computers", {"operation": "inspect", "source": "import os\nos.system('id')\nclass A:\n def f(self): pass"})["result"]
        self.assertTrue(result["ast_parse_valid"])
        self.assertEqual(result["functions"], ["f"])
        self.assertEqual(result["classes"], ["A"])
        self.assertEqual(result["import_statements"], 1)
        self.assertFalse(run_tool("computers", {"operation": "inspect", "source": "def x(:"})["result"]["ast_parse_valid"])
        self.assertTrue(run_tool("computers", {"operation": "inspect", "source": "return 42"})["result"]["ast_parse_valid"])

    def test_argument_validation_and_structured_errors(self):
        for name, args in [("unknown", {}), ("math", []), ("math", {"operation": "evaluate", "expression": "1", "secret": "x"}), ("biology", {"operation": "statistics", "sequence": "A", "kind": []})]:
            with self.subTest(name=name, args=args), self.assertRaises(ToolError) as raised:
                run_tool(name, args)
            self.assertEqual(set(raised.exception.to_dict()), {"error"})


if __name__ == "__main__":
    unittest.main()
