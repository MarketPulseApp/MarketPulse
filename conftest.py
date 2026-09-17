"""conftest.py — save this to the PROJECT ROOT:
    C:\\marketpulse\\MarketPulse\\conftest.py

This must live at the root (same folder as pyproject.toml) so pytest
loads it before collecting any test modules.

It adds  C:\\marketpulse\\MarketPulse\\app  to sys.path so that:
  from domain.xxx import ...   resolves to  app/domain/xxx.py
  from db.xxx    import ...   resolves to  app/db/xxx.py

It also aliases app.domain.* → domain.* so isinstance() works when
the db layer imports via "app.domain" and tests import via "domain".
"""

from __future__ import annotations

import importlib
import os
import sys
import types as _stdlib_types

# ── source root is the  app/  package directory ──────────────────────────────
# This file lives at:   <root>/conftest.py
# app/ source root is:  <root>/app/
_ROOT = os.path.dirname(os.path.abspath(__file__))
_APP_SRC = os.path.join(_ROOT, "app")

if _APP_SRC not in sys.path:
    sys.path.insert(0, _APP_SRC)

# ── alias app.domain.* → domain.* ────────────────────────────────────────────
# db layer uses:   from app.domain.news import NewsArticle
# test files use:  from domain.news import NewsArticle
# Both must be the SAME class object so isinstance() checks pass.
for _mod in ("news", "reddit", "sec", "explanation"):
    _canonical = f"domain.{_mod}"
    _alias = f"app.domain.{_mod}"
    if _canonical not in sys.modules:
        importlib.import_module(_canonical)
    if _alias not in sys.modules:
        sys.modules[_alias] = sys.modules[_canonical]

# Create lightweight package namespace entries for app and app.domain
if "app" not in sys.modules:
    _pkg = _stdlib_types.ModuleType("app")
    _pkg.__path__ = [_APP_SRC]
    sys.modules["app"] = _pkg
if "app.domain" not in sys.modules:
    _dpkg = _stdlib_types.ModuleType("app.domain")
    _dpkg.__path__ = [os.path.join(_APP_SRC, "domain")]
    sys.modules["app.domain"] = _dpkg

pytest_plugins = ["pytest_asyncio"]
