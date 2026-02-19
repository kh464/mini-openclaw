"""Python REPL tool — restricted builtins for safety."""

import io
import contextlib

from langchain_core.tools import tool as lc_tool, BaseTool

MAX_OUTPUT = 5000

# Restricted builtins: no file I/O, no imports, no exec/eval/compile
SAFE_BUILTINS = {
    "print": print, "len": len, "range": range, "int": int,
    "float": float, "str": str, "list": list, "dict": dict,
    "tuple": tuple, "set": set, "bool": bool, "abs": abs,
    "min": min, "max": max, "sum": sum, "sorted": sorted,
    "enumerate": enumerate, "zip": zip, "map": map, "filter": filter,
    "round": round, "type": type, "isinstance": isinstance,
    "hasattr": hasattr, "getattr": getattr, "repr": repr,
    "reversed": reversed, "any": any, "all": all,
    "True": True, "False": False, "None": None,
}


def create_python_repl_tool() -> BaseTool:

    @lc_tool
    def python_repl(code: str) -> str:
        """Execute Python code and return the output. Use for calculations and data processing."""
        stdout = io.StringIO()
        try:
            with contextlib.redirect_stdout(stdout):
                exec(code, {"__builtins__": SAFE_BUILTINS})
            output = stdout.getvalue().strip()
            if len(output) > MAX_OUTPUT:
                output = output[:MAX_OUTPUT] + "\n...[truncated]"
            return output or "(no output)"
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    return python_repl
