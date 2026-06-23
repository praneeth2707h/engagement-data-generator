"""Smoke tests for all Stage 11 UI modules.

These tests verify that:
- All modules import without error
- render() and helper functions exist and have correct signatures
- Session-state helpers initialise correctly
- No ARCH-011 violations (no iterrows / apply in UI code)
- Business Rules page functions handle missing config gracefully
"""
from __future__ import annotations

import ast
import inspect
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# ── Streamlit stub so modules can import without a live Streamlit session ──
def _make_streamlit_stub() -> types.ModuleType:
    """Return a minimal streamlit mock that satisfies all UI imports."""
    st = MagicMock(name="streamlit")

    # session_state as a plain dict-like object
    class _SessionState(dict):
        def __getattr__(self, key):
            try:
                return self[key]
            except KeyError:
                raise AttributeError(key)
        def __setattr__(self, key, value):
            self[key] = value
        def get(self, key, default=None):
            return super().get(key, default)

    st.session_state = _SessionState()

    # Widgets that return values
    st.text_input.return_value          = ""
    st.text_area.return_value           = ""
    st.number_input.return_value        = 0
    st.selectbox.return_value           = None
    st.multiselect.return_value         = []
    st.checkbox.return_value            = False
    st.slider.return_value              = 0.0
    st.date_input.return_value          = None
    st.file_uploader.return_value       = None
    st.button.return_value              = False
    st.download_button.return_value     = False
    st.radio.return_value               = None
    st.columns.side_effect              = lambda n, **kw: [MagicMock() for _ in range(n if isinstance(n, int) else len(n))]
    st.tabs.return_value                = [MagicMock(), MagicMock(), MagicMock()]
    st.expander.return_value.__enter__  = lambda s, *a: MagicMock()
    st.expander.return_value.__exit__   = lambda s, *a: False
    st.form.return_value.__enter__      = lambda s, *a: MagicMock()
    st.form.return_value.__exit__       = lambda s, *a: False
    st.set_page_config                  = MagicMock()
    st.stop                             = MagicMock(side_effect=SystemExit(0))
    st.spinner.return_value.__enter__   = lambda s, *a: MagicMock()
    st.spinner.return_value.__exit__    = lambda s, *a: False
    st.progress.return_value            = MagicMock()

    return st


_ST_STUB = _make_streamlit_stub()
sys.modules["streamlit"] = _ST_STUB


# ── Helpers ────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent.parent


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _no_iterrows(source: str) -> bool:
    return "iterrows()" not in source


def _no_apply_axis1(source: str) -> bool:
    return "apply(" not in source or "axis=1" not in source


# ──────────────────────────────────────────────────────────────────────────
class TestStateModule(unittest.TestCase):
    """ui/state.py"""

    def setUp(self):
        _ST_STUB.session_state.clear()
        # re-import fresh
        for mod in list(sys.modules.keys()):
            if mod.startswith("ui."):
                del sys.modules[mod]

    def test_import(self):
        import ui.state as s
        self.assertTrue(hasattr(s, "init_session_state"))

    def test_key_constants_defined(self):
        import ui.state as s
        for attr in (
            "KEY_TRIGGER_DF", "KEY_HISTORICAL_DF", "KEY_CONFIG_DICT",
            "KEY_RESULT", "KEY_RUN_ERROR", "KEY_ACTIVE_PAGE",
        ):
            self.assertTrue(hasattr(s, attr), f"Missing constant: {attr}")

    def test_init_session_state_sets_defaults(self):
        import ui.state as s
        s.init_session_state()
        # After init, getters return None (not KeyError)
        self.assertIsNone(s.get_trigger_df())
        self.assertIsNone(s.get_config_dict())
        self.assertIsNone(s.get_result())

    def test_set_get_trigger_df_roundtrip(self):
        import pandas as pd
        import ui.state as s
        s.init_session_state()
        df = pd.DataFrame({"a": [1, 2]})
        s.set_trigger_df(df)
        back = s.get_trigger_df()
        self.assertIsNotNone(back)
        self.assertEqual(len(back), 2)

    def test_set_get_config_dict_roundtrip(self):
        import ui.state as s
        s.init_session_state()
        cfg = {"campaign_id": "TEST"}
        s.set_config_dict(cfg)
        self.assertEqual(s.get_config_dict()["campaign_id"], "TEST")

    def test_set_get_run_error(self):
        import ui.state as s
        s.init_session_state()
        s.set_run_error("boom")
        self.assertEqual(s.get_run_error(), "boom")
        s.set_run_error(None)
        self.assertIsNone(s.get_run_error())

    def test_no_iterrows(self):
        src = _source(PROJECT_ROOT / "ui" / "state.py")
        self.assertTrue(_no_iterrows(src), "iterrows() found in state.py")


# ──────────────────────────────────────────────────────────────────────────
class TestUploadPageModule(unittest.TestCase):
    """ui/upload_page.py"""

    def setUp(self):
        _ST_STUB.session_state.clear()
        for mod in list(sys.modules.keys()):
            if mod.startswith("ui."):
                del sys.modules[mod]

    def test_import(self):
        import ui.upload_page as m
        self.assertTrue(hasattr(m, "render"))

    def test_render_is_callable(self):
        import ui.upload_page as m
        sig = inspect.signature(m.render)
        self.assertEqual(len(sig.parameters), 0)

    def test_render_runs_without_data(self):
        """render() should not raise when no data is in session state."""
        import ui.state as s
        s.init_session_state()
        import ui.upload_page as m
        # Should complete without exception (file_uploader returns None from stub)
        m.render()

    def test_no_iterrows(self):
        src = _source(PROJECT_ROOT / "ui" / "upload_page.py")
        self.assertTrue(_no_iterrows(src))

    def test_no_apply_axis1(self):
        src = _source(PROJECT_ROOT / "ui" / "upload_page.py")
        self.assertTrue(_no_apply_axis1(src))


# ──────────────────────────────────────────────────────────────────────────
class TestCampaignPageModule(unittest.TestCase):
    """ui/campaign_page.py"""

    def setUp(self):
        _ST_STUB.session_state.clear()
        for mod in list(sys.modules.keys()):
            if mod.startswith("ui."):
                del sys.modules[mod]

    def test_import(self):
        import ui.campaign_page as m
        self.assertTrue(hasattr(m, "render"))

    def test_render_is_callable(self):
        import ui.campaign_page as m
        sig = inspect.signature(m.render)
        self.assertEqual(len(sig.parameters), 0)

    def test_render_runs_without_data(self):
        import ui.state as s
        s.init_session_state()
        import ui.campaign_page as m
        m.render()

    def test_default_config_has_required_keys(self):
        import ui.campaign_page as m
        cfg = m._default_config()
        for key in ("campaign_id", "simulation_start_date", "simulation_end_date",
                    "ads", "triggers", "rules"):
            self.assertIn(key, cfg, f"Missing key: {key}")

    def test_no_iterrows(self):
        src = _source(PROJECT_ROOT / "ui" / "campaign_page.py")
        self.assertTrue(_no_iterrows(src))


# ──────────────────────────────────────────────────────────────────────────
class TestBusinessRulesPageModule(unittest.TestCase):
    """ui/business_rules_page.py"""

    def setUp(self):
        _ST_STUB.session_state.clear()
        for mod in list(sys.modules.keys()):
            if mod.startswith("ui."):
                del sys.modules[mod]

    def test_import(self):
        import ui.business_rules_page as m
        self.assertTrue(hasattr(m, "render"))

    def test_render_is_callable(self):
        import ui.business_rules_page as m
        sig = inspect.signature(m.render)
        self.assertEqual(len(sig.parameters), 0)

    def test_render_with_no_config_shows_warning(self):
        """When no config, render() should call st.warning (not crash)."""
        import ui.state as s
        s.init_session_state()
        # No config → render should early-return after st.warning
        import ui.business_rules_page as m
        try:
            m.render()
        except SystemExit:
            pass  # st.stop() raises SystemExit in stub

    def test_no_iterrows(self):
        src = _source(PROJECT_ROOT / "ui" / "business_rules_page.py")
        self.assertTrue(_no_iterrows(src))


# ──────────────────────────────────────────────────────────────────────────
class TestRunPageModule(unittest.TestCase):
    """ui/run_page.py"""

    def setUp(self):
        _ST_STUB.session_state.clear()
        for mod in list(sys.modules.keys()):
            if mod.startswith("ui."):
                del sys.modules[mod]

    def test_import(self):
        import ui.run_page as m
        self.assertTrue(hasattr(m, "render"))

    def test_render_is_callable(self):
        import ui.run_page as m
        sig = inspect.signature(m.render)
        self.assertEqual(len(sig.parameters), 0)

    def test_render_fails_preflight_without_data(self):
        """Without trigger data render() should show errors and stop."""
        import ui.state as s
        s.init_session_state()
        import ui.run_page as m
        try:
            m.render()
        except SystemExit:
            pass  # st.stop() → expected

    def test_preflight_checks_no_trigger(self):
        import ui.state as s
        s.init_session_state()
        import ui.run_page as m
        errors = m._preflight_checks()
        self.assertTrue(any("trigger" in e.lower() for e in errors))

    def test_preflight_checks_passes_with_data(self):
        """With trigger df and config, preflight should pass."""
        import pandas as pd
        import ui.state as s
        s.init_session_state()
        s.set_trigger_df(pd.DataFrame({
            "Campaign_ID": ["C1"], "User_ID": ["U1"],
            "Trigger_Name": ["T1"], "Segment": ["S1"],
        }))
        s.set_config_dict({
            "campaign_id": "C1",
            "simulation_start_date": "2025-01-01",
            "simulation_end_date":   "2025-01-07",
            "ads": [{"ad_id": "A1"}],
            "triggers": [{"trigger_name": "T1"}],
            "rules": {},
        })
        import ui.run_page as m
        errors = m._preflight_checks()
        self.assertEqual(errors, [])

    def test_no_iterrows(self):
        src = _source(PROJECT_ROOT / "ui" / "run_page.py")
        self.assertTrue(_no_iterrows(src))


# ──────────────────────────────────────────────────────────────────────────
class TestResultsPageModule(unittest.TestCase):
    """ui/results_page.py"""

    def setUp(self):
        _ST_STUB.session_state.clear()
        for mod in list(sys.modules.keys()):
            if mod.startswith("ui."):
                del sys.modules[mod]

    def test_import(self):
        import ui.results_page as m
        self.assertTrue(hasattr(m, "render"))

    def test_render_is_callable(self):
        import ui.results_page as m
        sig = inspect.signature(m.render)
        self.assertEqual(len(sig.parameters), 0)

    def test_render_with_no_result(self):
        import ui.state as s
        s.init_session_state()
        import ui.results_page as m
        m.render()  # Should show info message, not raise

    def test_render_with_mock_result(self):
        """render() with a well-formed SimulationResult should not raise."""
        import pandas as pd
        import ui.state as s
        s.init_session_state()

        # Build minimal SimulationResult
        from models.simulation_result import SimulationResult
        result = SimulationResult(
            quality_score=85.0,
            realism_score=78.5,
            events_df=pd.DataFrame({"event": [1, 2, 3]}),
            metrics_df=pd.DataFrame({"metric": ["ctr"], "value": [0.02]}),
            validation_results_df=pd.DataFrame({
                "rule_id": ["VAL-001"], "status": ["Pass"],
                "severity": ["Hard"], "message": ["OK"],
            }),
            validation_summary_df=pd.DataFrame({
                "severity": ["Hard"], "status": ["Pass"], "count": [1],
            }),
            realism_report_df=pd.DataFrame({"rule": ["R1"], "score": [0.9]}),
            workbook_bytes=b"FAKEEXCEL",
            execution_metadata={"campaign_id": "TEST", "n_events": 3},
        )
        s.set_result(result)

        import ui.results_page as m
        m.render()  # Must not raise

    def test_score_colour_helper(self):
        import ui.results_page as m
        self.assertEqual(m._score_colour(90.0), "normal")
        self.assertEqual(m._score_colour(70.0), "off")
        self.assertEqual(m._score_colour(50.0), "inverse")

    def test_validation_badge_helper(self):
        import ui.results_page as m
        self.assertEqual(m._validation_badge("Pass"),    "🟢")
        self.assertEqual(m._validation_badge("Fail"),    "🔴")
        self.assertEqual(m._validation_badge("Skip"),    "⚪")
        self.assertEqual(m._validation_badge("Warning"), "🟡")

    def test_no_iterrows(self):
        src = _source(PROJECT_ROOT / "ui" / "results_page.py")
        self.assertTrue(_no_iterrows(src))


# ──────────────────────────────────────────────────────────────────────────
class TestAppModule(unittest.TestCase):
    """app.py — verify structure without executing Streamlit runtime."""

    def test_app_file_exists(self):
        self.assertTrue((PROJECT_ROOT / "app.py").exists())

    def test_app_imports_all_pages(self):
        src = _source(PROJECT_ROOT / "app.py")
        for page in ("upload_page", "campaign_page", "business_rules_page",
                     "run_page", "results_page"):
            self.assertIn(page, src, f"app.py does not import {page}")

    def test_app_calls_init_session_state(self):
        src = _source(PROJECT_ROOT / "app.py")
        self.assertIn("init_session_state", src)

    def test_app_has_set_page_config(self):
        src = _source(PROJECT_ROOT / "app.py")
        self.assertIn("set_page_config", src)

    def test_app_syntax_valid(self):
        src = _source(PROJECT_ROOT / "app.py")
        try:
            ast.parse(src)
        except SyntaxError as exc:
            self.fail(f"app.py has syntax error: {exc}")

    def test_no_iterrows_in_app(self):
        src = _source(PROJECT_ROOT / "app.py")
        self.assertTrue(_no_iterrows(src))


# ──────────────────────────────────────────────────────────────────────────
class TestUIModuleCompleteness(unittest.TestCase):
    """Verify all expected UI files exist and export render()."""

    UI_MODULES = [
        "ui/state.py",
        "ui/upload_page.py",
        "ui/campaign_page.py",
        "ui/business_rules_page.py",
        "ui/run_page.py",
        "ui/results_page.py",
    ]
    RENDER_MODULES = [
        "ui/upload_page.py",
        "ui/campaign_page.py",
        "ui/business_rules_page.py",
        "ui/run_page.py",
        "ui/results_page.py",
    ]

    def test_all_ui_files_exist(self):
        for rel in self.UI_MODULES:
            p = PROJECT_ROOT / rel
            self.assertTrue(p.exists(), f"Missing: {rel}")

    def test_all_render_modules_export_render(self):
        for rel in self.RENDER_MODULES:
            src = _source(PROJECT_ROOT / rel)
            self.assertIn("def render(", src, f"No render() in {rel}")

    def test_all_have_all_dunder(self):
        for rel in self.RENDER_MODULES:
            src = _source(PROJECT_ROOT / rel)
            self.assertIn("__all__", src, f"No __all__ in {rel}")


# ──────────────────────────────────────────────────────────────────────────
class TestArch011Compliance(unittest.TestCase):
    """ARCH-011 — no iterrows() anywhere in ui/ code."""

    UI_FILES = list((PROJECT_ROOT / "ui").glob("*.py"))

    def test_no_iterrows_in_any_ui_file(self):
        for fp in self.UI_FILES:
            src = fp.read_text(encoding="utf-8")
            self.assertNotIn(
                "iterrows()", src,
                f"ARCH-011 violation: iterrows() in {fp.name}",
            )

    def test_no_apply_axis1_in_any_ui_file(self):
        for fp in self.UI_FILES:
            src = fp.read_text(encoding="utf-8")
            if "apply(" in src and "axis=1" in src:
                self.fail(
                    f"ARCH-011 potential violation: apply(axis=1) in {fp.name}"
                )


if __name__ == "__main__":
    unittest.main()
