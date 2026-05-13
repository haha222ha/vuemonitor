import importlib.util, sys, os

_here = os.path.dirname(os.path.abspath(__file__))
_dev_root = os.path.normpath(os.path.join(_here, "..", "..", "..", "shared"))


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_fg_path = os.path.join(_dev_root, "constants", "feature_gates.py")
_ec_path = os.path.join(_dev_root, "constants", "error_codes.py")

if os.path.isfile(_fg_path):
    feature_gates = _load_module("shared.constants.feature_gates", _fg_path)
    sys.modules["shared.constants.feature_gates"] = feature_gates

if os.path.isfile(_ec_path):
    error_codes = _load_module("shared.constants.error_codes", _ec_path)
    sys.modules["shared.constants.error_codes"] = error_codes
