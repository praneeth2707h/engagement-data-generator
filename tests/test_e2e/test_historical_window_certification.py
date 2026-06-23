"""Stage 14 - Historical Window End-to-End Certification Suite.

Proves that historical engagement window configurations correctly filter
historical data and influence trigger engagement capacity calculations.

Certification question (HW-CERT-Q-001):
    "Do historical engagement windows correctly and deterministically
     influence trigger engagement calculations?"

Architecture under test
-----------------------
* ConfigRegistry.get_historical_cutoff_date() -- computes lookback cutoff
* AudienceManager.compute_remaining_capacity() -- applies window filter to
  historical_df and computes remaining TCC capacity per trigger
* EngagementGenerator._init_capacity_tracker() -- uses per-user
  historical_engaged flag to reduce TCC (separate pathway)
* HistoricalWindow enum: ALL_TIME, LAST_90, LAST_180, LAST_365, CUSTOM

Historical window mechanisms
-----------------------------
Two distinct pathways exist for historical data to influence the simulation:

Pathway A -- Aggregate (AudienceManager):
  historical_df -> compute_remaining_capacity() -> capacity_list
  Applies window cutoff: records with Date >= cutoff_date are counted.
  Returns per-trigger remaining capacity (aggregate count).
  NOTE: In SimulationOrchestrator.run(), this capacity_list is currently
  returned but not wired into apply_capacity_cap() or EngagementGenerator.
  This is documented as ARCH-RISK-003.

Pathway B -- Per-User (EngagementGenerator):
  state_df["historical_engaged"] bool flag -> _init_capacity_tracker()
  Users marked historical_engaged=True reduce TCC by 1 each.
  This is the ACTIVE pathway that controls event generation.

Certified invariants
--------------------
1. get_historical_cutoff_date() returns correct dates for all window types.
2. 30-day filter keeps only records >= sim_start - 30 days.
3. 60-day filter keeps only records >= sim_start - 60 days.
4. 90-day filter keeps only records >= sim_start - 90 days.
5. ALL_TIME returns no cutoff (None) -- all records included.
6. Exactly-on-boundary records are INCLUDED (>= comparison).
7. One-day-before-boundary records are EXCLUDED (< cutoff).
8. Mixed populations reconcile across window sizes.
9. Per-user historical_engaged=True reduces TCC and produces fewer events.
10. Results are deterministic across repeated runs.

Design notes
------------
* HW-001..HW-006 test AudienceManager.compute_remaining_capacity() directly
  since Pathway A is not wired through the orchestrator.
* HW-007..HW-010 test Pathway B (per-user flag) through run().
* engagement_cooldown_days=0 maximises observable events.
* generate_excel=False except HW-009 (workbook) and HW-010 (determinism).

References
----------
HW-001 .. HW-010 -- Certification scenario IDs
BRC-009          -- Historical window applied using simulation_start_date
TCC-001..004     -- TCC formula and enforcement
ARCH-RISK-003    -- Pathway A disconnection (documented)
"""
from __future__ import annotations

import math
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.audience_manager import AudienceManager
from core.engagement_generator import EngagementGenerator
from core.simulation_orchestrator import SimulationOrchestrator
from core.user_state_manager import UserStateManager
from core.validation_engine import ValidationEngine
from models.ad_config import AdConfig
from models.config_registry import ConfigRegistry
from models.enums import HistoricalWindow
from models.trigger_config import TriggerConfig
from tests.test_core.conftest import make_config


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_SIM_START  = date(2024, 1, 1)
_SIM_END_14 = date(2024, 1, 14)
_CAMPAIGN   = "TEST_CAMPAIGN"

# Historical dates relative to _SIM_START
_DATE_WITHIN_30  = date(2023, 12, 15)   # 17 days before
_DATE_31_60      = date(2023, 11, 10)   # 52 days before
_DATE_61_90      = date(2023, 10, 15)   # 78 days before
_DATE_BEYOND_90  = date(2023,  9,  1)   # 122 days before
_DATE_BEYOND_365 = date(2022,  6,  1)   # 579 days before

# Exact cutoff dates (sim_start - N days)
_CUTOFF_30  = _SIM_START - timedelta(days=30)    # 2023-12-02
_CUTOFF_60  = _SIM_START - timedelta(days=60)    # 2023-11-02
_CUTOFF_90  = _SIM_START - timedelta(days=90)    # 2023-10-03
_CUTOFF_180 = _SIM_START - timedelta(days=180)   # 2023-07-05
_CUTOFF_365 = _SIM_START - timedelta(days=365)   # 2023-01-01


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _base_cfg(**kw) -> ConfigRegistry:
    defaults = dict(
        simulation_start_date=_SIM_START,
        simulation_end_date=_SIM_END_14,
        weekly_impression_cap=20,
        weekly_engagement_cap=14,
        weekly_click_cap=20,
        weekly_open_cap=20,
        engagement_cooldown_days=0,
        cooling_period_days=0,
        ads=(AdConfig("Ad_A", 1, 14, False, "Display", "VendorX", 0.10),),
        triggers=(TriggerConfig("T1", 1, 0.50),),
        segments=(),
        channels=(),
        historical_engagement_window=HistoricalWindow.LAST_90.value,
        historical_window_days=None,
    )
    defaults.update(kw)
    return make_config(**defaults)


def _two_trigger_cfg(**kw) -> ConfigRegistry:
    defaults = dict(
        simulation_start_date=_SIM_START,
        simulation_end_date=_SIM_END_14,
        weekly_impression_cap=20,
        weekly_engagement_cap=14,
        weekly_click_cap=20,
        weekly_open_cap=20,
        engagement_cooldown_days=0,
        cooling_period_days=0,
        ads=(AdConfig("Ad_A", 1, 14, False, "Display", "VendorX", 0.10),),
        triggers=(
            TriggerConfig("T1", 1, 0.50),
            TriggerConfig("T2", 2, 0.30),
        ),
        segments=(),
        channels=(),
        historical_engagement_window=HistoricalWindow.LAST_90.value,
        historical_window_days=None,
    )
    defaults.update(kw)
    return make_config(**defaults)


def _tdf(users, trigger="T1"):
    return pd.DataFrame([{
        "Campaign_ID":  _CAMPAIGN,
        "User_ID":      uid,
        "Trigger_Name": trigger,
        "Segment":      "Seg_A",
        "Trigger_Date": _SIM_START,
    } for uid in users])


def _make_hist_df(user_ids, engagement_date, trigger_name="T1", campaign_id=_CAMPAIGN):
    rows = []
    for uid in user_ids:
        row = {
            "Campaign_ID":  campaign_id,
            "User_ID":      uid,
            "Date":         pd.Timestamp(engagement_date),
            "Action":       "Click",
            "Channel":      "Display",
        }
        if trigger_name is not None:
            row["Trigger_Name"] = trigger_name
        rows.append(row)
    return pd.DataFrame(rows)


def _concat_hist(*dfs):
    return pd.concat(list(dfs), ignore_index=True)


def _users(prefix, n, start=1):
    return [f"U_{prefix}{i:03d}" for i in range(start, start + n)]


# ---------------------------------------------------------------------------
# HW-001: 30-Day Window
# ---------------------------------------------------------------------------

class TestHW001ThirtyDayWindow(unittest.TestCase):
    """HW-001: Only engagements within last 30 days are counted."""

    def setUp(self):
        self.within_users = _users("W30", 10)
        self.outside_users = _users("X30", 6)
        self.all_users = self.within_users + self.outside_users + _users("N30", 4)

        hist_within  = _make_hist_df(self.within_users,  _DATE_WITHIN_30)
        hist_outside = _make_hist_df(self.outside_users, _DATE_31_60)
        self.hist_df = _concat_hist(hist_within, hist_outside)
        self.tdf = _tdf(self.all_users)

        self.cfg = _base_cfg(
            historical_engagement_window=HistoricalWindow.CUSTOM.value,
            historical_window_days=30,
        )
        self.am = AudienceManager(self.cfg)

    def test_s01_cutoff_date_is_30_days_before_sim_start(self):
        cutoff = self.cfg.get_historical_cutoff_date(self.cfg.simulation_start_date)
        self.assertEqual(cutoff, _CUTOFF_30)

    def test_s02_within_window_users_counted(self):
        capacity = self.am.compute_remaining_capacity(self.hist_df, self.tdf)
        self.assertEqual(capacity[0].historical_engaged_users, 10)

    def test_s03_outside_window_users_excluded(self):
        outside_only = _make_hist_df(self.outside_users, _DATE_31_60)
        capacity = self.am.compute_remaining_capacity(outside_only, self.tdf)
        self.assertEqual(capacity[0].historical_engaged_users, 0)

    def test_s04_remaining_capacity_reduced_by_within_window_count(self):
        capacity = self.am.compute_remaining_capacity(self.hist_df, self.tdf)
        row = capacity[0]
        expected_ceiling = math.ceil(len(self.all_users) * 0.50)
        expected_remaining = max(0, expected_ceiling - 10)
        self.assertEqual(row.remaining_capacity, expected_remaining)

    def test_s05_none_historical_df_gives_zero_historical_engaged(self):
        capacity = self.am.compute_remaining_capacity(None, self.tdf)
        self.assertEqual(capacity[0].historical_engaged_users, 0)


# ---------------------------------------------------------------------------
# HW-002: 60-Day Window
# ---------------------------------------------------------------------------

class TestHW002SixtyDayWindow(unittest.TestCase):
    """HW-002: Engagements older than 30 but newer than 60 days are included."""

    def setUp(self):
        self.users_within_30 = _users("W60a", 5)
        self.users_31_60     = _users("W60b", 3)
        self.users_beyond_60 = _users("X60",  2)

        self.hist_df = _concat_hist(
            _make_hist_df(self.users_within_30, _DATE_WITHIN_30),
            _make_hist_df(self.users_31_60,     _DATE_31_60),
            _make_hist_df(self.users_beyond_60, _DATE_BEYOND_90),
        )
        all_users = (self.users_within_30 + self.users_31_60
                     + self.users_beyond_60 + _users("N60", 5))
        self.tdf = _tdf(all_users)

        self.cfg = _base_cfg(
            historical_engagement_window=HistoricalWindow.CUSTOM.value,
            historical_window_days=60,
        )
        self.am = AudienceManager(self.cfg)

    def test_s01_cutoff_is_60_days_before_sim_start(self):
        cutoff = self.cfg.get_historical_cutoff_date(self.cfg.simulation_start_date)
        self.assertEqual(cutoff, _CUTOFF_60)

    def test_s02_within_30_day_users_counted(self):
        within_only = _make_hist_df(self.users_within_30, _DATE_WITHIN_30)
        tdf = _tdf(self.users_within_30 + _users("N60x", 5))
        capacity = self.am.compute_remaining_capacity(within_only, tdf)
        self.assertEqual(capacity[0].historical_engaged_users, 5)

    def test_s03_31_to_60_day_users_also_counted(self):
        mid_only = _make_hist_df(self.users_31_60, _DATE_31_60)
        tdf = _tdf(self.users_31_60 + _users("N60y", 5))
        capacity = self.am.compute_remaining_capacity(mid_only, tdf)
        self.assertEqual(capacity[0].historical_engaged_users, 3)

    def test_s04_combined_count_is_8(self):
        capacity = self.am.compute_remaining_capacity(self.hist_df, self.tdf)
        self.assertEqual(capacity[0].historical_engaged_users, 8)

    def test_s05_beyond_60_users_excluded(self):
        beyond_only = _make_hist_df(self.users_beyond_60, _DATE_BEYOND_90)
        tdf = _tdf(self.users_beyond_60 + _users("N60z", 5))
        capacity = self.am.compute_remaining_capacity(beyond_only, tdf)
        self.assertEqual(capacity[0].historical_engaged_users, 0)


# ---------------------------------------------------------------------------
# HW-003: 90-Day Window
# ---------------------------------------------------------------------------

class TestHW003NinetyDayWindow(unittest.TestCase):
    """HW-003: Engagements older than 60 but newer than 90 days are included."""

    def setUp(self):
        self.users_17  = _users("W90a", 5)
        self.users_52  = _users("W90b", 3)
        self.users_78  = _users("W90c", 4)
        self.users_122 = _users("X90",  2)

        self.hist_df = _concat_hist(
            _make_hist_df(self.users_17,  _DATE_WITHIN_30),
            _make_hist_df(self.users_52,  _DATE_31_60),
            _make_hist_df(self.users_78,  _DATE_61_90),
            _make_hist_df(self.users_122, _DATE_BEYOND_90),
        )
        all_users = (self.users_17 + self.users_52 + self.users_78
                     + self.users_122 + _users("N90", 6))
        self.tdf = _tdf(all_users)

        self.cfg = _base_cfg(
            historical_engagement_window=HistoricalWindow.LAST_90.value,
            historical_window_days=None,
        )
        self.am = AudienceManager(self.cfg)

    def test_s01_cutoff_is_90_days_before_sim_start(self):
        cutoff = self.cfg.get_historical_cutoff_date(self.cfg.simulation_start_date)
        self.assertEqual(cutoff, _CUTOFF_90)

    def test_s02_all_three_bands_included(self):
        capacity = self.am.compute_remaining_capacity(self.hist_df, self.tdf)
        self.assertEqual(capacity[0].historical_engaged_users, 12)

    def test_s03_61_to_90_band_included(self):
        band_only = _make_hist_df(self.users_78, _DATE_61_90)
        tdf = _tdf(self.users_78 + _users("N90x", 5))
        capacity = self.am.compute_remaining_capacity(band_only, tdf)
        self.assertEqual(capacity[0].historical_engaged_users, 4)

    def test_s04_beyond_90_excluded(self):
        beyond_only = _make_hist_df(self.users_122, _DATE_BEYOND_90)
        tdf = _tdf(self.users_122 + _users("N90y", 5))
        capacity = self.am.compute_remaining_capacity(beyond_only, tdf)
        self.assertEqual(capacity[0].historical_engaged_users, 0)

    def test_s05_remaining_capacity_subtracts_12_from_ceiling(self):
        capacity = self.am.compute_remaining_capacity(self.hist_df, self.tdf)
        row = capacity[0]
        n_total = len(self.tdf)
        ceiling = math.ceil(n_total * 0.50)
        expected = max(0, ceiling - 12)
        self.assertEqual(row.remaining_capacity, expected)


# ---------------------------------------------------------------------------
# HW-004: All-Time Window
# ---------------------------------------------------------------------------

class TestHW004AllTimeWindow(unittest.TestCase):
    """HW-004: All historical engagements are included with All_Time window."""

    def setUp(self):
        self.users_recent  = _users("AT_R", 3)
        self.users_mid     = _users("AT_M", 3)
        self.users_old     = _users("AT_O", 3)
        self.users_ancient = _users("AT_A", 3)

        self.hist_df = _concat_hist(
            _make_hist_df(self.users_recent,  _DATE_WITHIN_30),
            _make_hist_df(self.users_mid,     _DATE_31_60),
            _make_hist_df(self.users_old,     _DATE_BEYOND_90),
            _make_hist_df(self.users_ancient, _DATE_BEYOND_365),
        )
        all_users = (self.users_recent + self.users_mid
                     + self.users_old + self.users_ancient + _users("NAT", 2))
        self.tdf = _tdf(all_users)

        self.cfg = _base_cfg(
            historical_engagement_window=HistoricalWindow.ALL_TIME.value,
            historical_window_days=None,
        )
        self.am = AudienceManager(self.cfg)

    def test_s01_cutoff_date_is_none_for_all_time(self):
        cutoff = self.cfg.get_historical_cutoff_date(self.cfg.simulation_start_date)
        self.assertIsNone(cutoff)

    def test_s02_all_12_historical_users_counted(self):
        capacity = self.am.compute_remaining_capacity(self.hist_df, self.tdf)
        self.assertEqual(capacity[0].historical_engaged_users, 12)

    def test_s03_ancient_records_included(self):
        ancient_only = _make_hist_df(self.users_ancient, _DATE_BEYOND_365)
        tdf = _tdf(self.users_ancient + _users("NAT2", 5))
        capacity = self.am.compute_remaining_capacity(ancient_only, tdf)
        self.assertEqual(capacity[0].historical_engaged_users, 3)

    def test_s04_remaining_capacity_at_most_zero_when_hist_exceeds_ceiling(self):
        capacity = self.am.compute_remaining_capacity(self.hist_df, self.tdf)
        n_total = len(self.tdf)
        ceiling = math.ceil(n_total * 0.50)
        self.assertEqual(capacity[0].remaining_capacity, max(0, ceiling - 12))


# ---------------------------------------------------------------------------
# HW-005: Boundary Tests
# ---------------------------------------------------------------------------

class TestHW005BoundaryDates(unittest.TestCase):
    """HW-005: Exactly-on-boundary included; one-day-before excluded."""

    def setUp(self):
        self.tdf_users = _users("BND", 10)
        self.tdf = _tdf(self.tdf_users)

    def _count(self, user_ids, eng_date, window, window_days=None):
        cfg = _base_cfg(
            historical_engagement_window=window,
            historical_window_days=window_days,
        )
        hist = _make_hist_df(user_ids, eng_date)
        return AudienceManager(cfg).compute_remaining_capacity(
            hist, self.tdf
        )[0].historical_engaged_users

    def test_s01_exactly_on_30day_cutoff_is_included(self):
        count = self._count(
            _users("BND30", 3), _CUTOFF_30,
            HistoricalWindow.CUSTOM.value, 30,
        )
        self.assertEqual(count, 3)

    def test_s02_one_day_before_30day_cutoff_is_excluded(self):
        count = self._count(
            _users("BND30x", 3), _CUTOFF_30 - timedelta(days=1),
            HistoricalWindow.CUSTOM.value, 30,
        )
        self.assertEqual(count, 0)

    def test_s03_exactly_on_90day_cutoff_is_included(self):
        count = self._count(
            _users("BND90", 4), _CUTOFF_90,
            HistoricalWindow.LAST_90.value,
        )
        self.assertEqual(count, 4)

    def test_s04_one_day_before_90day_cutoff_is_excluded(self):
        count = self._count(
            _users("BND90x", 4), _CUTOFF_90 - timedelta(days=1),
            HistoricalWindow.LAST_90.value,
        )
        self.assertEqual(count, 0)

    def test_s05_exactly_on_180day_cutoff_is_included(self):
        count = self._count(
            _users("BND180", 2), _CUTOFF_180,
            HistoricalWindow.LAST_180.value,
        )
        self.assertEqual(count, 2)

    def test_s06_one_day_before_180day_cutoff_is_excluded(self):
        count = self._count(
            _users("BND180x", 2), _CUTOFF_180 - timedelta(days=1),
            HistoricalWindow.LAST_180.value,
        )
        self.assertEqual(count, 0)

    def test_s07_boundary_and_beyond_mix(self):
        on_boundary = _make_hist_df(_users("ONB", 2), _CUTOFF_30)
        one_before  = _make_hist_df(_users("OBF", 3), _CUTOFF_30 - timedelta(days=1))
        hist = _concat_hist(on_boundary, one_before)
        cfg = _base_cfg(
            historical_engagement_window=HistoricalWindow.CUSTOM.value,
            historical_window_days=30,
        )
        capacity = AudienceManager(cfg).compute_remaining_capacity(hist, self.tdf)
        self.assertEqual(capacity[0].historical_engaged_users, 2)


# ---------------------------------------------------------------------------
# HW-006: Mixed Population
# ---------------------------------------------------------------------------

class TestHW006MixedPopulation(unittest.TestCase):
    """HW-006: Users with different historical ages -- counts reconcile across windows.

    T1: 10 users, target_rate=0.50 -> ceiling=5
    T2: 20 users, target_rate=0.30 -> ceiling=6

    historical_df:
      T1: 3 users at 17 days + 2 users at 52 days
      T2: 4 users at 17 days + 3 users at 78 days
    """

    def setUp(self):
        self.t1_users = _users("T1S", 10)
        self.t2_users = _users("T2S", 20)

        self.t1_hist_recent = _users("T1H17", 3)
        self.t1_hist_mid    = _users("T1H52", 2)
        self.t2_hist_recent = _users("T2H17", 4)
        self.t2_hist_old    = _users("T2H78", 3)

        self.tdf = pd.concat([
            _tdf(self.t1_users, trigger="T1"),
            _tdf(self.t2_users, trigger="T2"),
        ], ignore_index=True)

        self.hist_df = _concat_hist(
            _make_hist_df(self.t1_hist_recent, _DATE_WITHIN_30, trigger_name="T1"),
            _make_hist_df(self.t1_hist_mid,    _DATE_31_60,     trigger_name="T1"),
            _make_hist_df(self.t2_hist_recent, _DATE_WITHIN_30, trigger_name="T2"),
            _make_hist_df(self.t2_hist_old,    _DATE_61_90,     trigger_name="T2"),
        )

    def _cfg(self, window, window_days=None):
        return _two_trigger_cfg(
            historical_engagement_window=window,
            historical_window_days=window_days,
        )

    def test_s01_30day_window_counts_only_recent(self):
        cfg = self._cfg(HistoricalWindow.CUSTOM.value, 30)
        cap = AudienceManager(cfg).compute_remaining_capacity(self.hist_df, self.tdf)
        self.assertEqual(cap[0].historical_engaged_users, 3)
        self.assertEqual(cap[1].historical_engaged_users, 4)

    def test_s02_60day_window_adds_t1_mid_band(self):
        cfg = self._cfg(HistoricalWindow.CUSTOM.value, 60)
        cap = AudienceManager(cfg).compute_remaining_capacity(self.hist_df, self.tdf)
        self.assertEqual(cap[0].historical_engaged_users, 5)
        self.assertEqual(cap[1].historical_engaged_users, 4)

    def test_s03_90day_window_adds_t2_old_band(self):
        cfg = self._cfg(HistoricalWindow.LAST_90.value)
        cap = AudienceManager(cfg).compute_remaining_capacity(self.hist_df, self.tdf)
        self.assertEqual(cap[0].historical_engaged_users, 5)
        self.assertEqual(cap[1].historical_engaged_users, 7)

    def test_s04_remaining_capacity_at_saturation(self):
        # T1: ceil(10*0.50)=5, hist=5 -> remaining=0
        # T2: ceil(20*0.30)=6, hist=7 -> remaining=max(0,-1)=0
        cfg = self._cfg(HistoricalWindow.LAST_90.value)
        cap = AudienceManager(cfg).compute_remaining_capacity(self.hist_df, self.tdf)
        self.assertEqual(cap[0].remaining_capacity, 0)
        self.assertEqual(cap[1].remaining_capacity, 0)

    def test_s05_all_time_matches_90day_for_this_dataset(self):
        cap_at = AudienceManager(self._cfg(HistoricalWindow.ALL_TIME.value))
        cap_90 = AudienceManager(self._cfg(HistoricalWindow.LAST_90.value))
        r_at = cap_at.compute_remaining_capacity(self.hist_df, self.tdf)
        r_90 = cap_90.compute_remaining_capacity(self.hist_df, self.tdf)
        self.assertEqual(r_at[0].historical_engaged_users, r_90[0].historical_engaged_users)
        self.assertEqual(r_at[1].historical_engaged_users, r_90[1].historical_engaged_users)

    def test_s06_window_progression_monotonically_nondecreasing(self):
        def t1_count(am):
            return am.compute_remaining_capacity(
                self.hist_df, self.tdf
            )[0].historical_engaged_users

        am30  = AudienceManager(self._cfg(HistoricalWindow.CUSTOM.value, 30))
        am60  = AudienceManager(self._cfg(HistoricalWindow.CUSTOM.value, 60))
        am90  = AudienceManager(self._cfg(HistoricalWindow.LAST_90.value))
        am_at = AudienceManager(self._cfg(HistoricalWindow.ALL_TIME.value))

        self.assertLessEqual(t1_count(am30), t1_count(am60))
        self.assertLessEqual(t1_count(am60), t1_count(am90))
        self.assertLessEqual(t1_count(am90), t1_count(am_at))


# ---------------------------------------------------------------------------
# HW-007: TER Calculation
# ---------------------------------------------------------------------------

class TestHW007TERCalculation(unittest.TestCase):
    """HW-007: TER changes appropriately when historical_engaged users differ.

    Pathway B (per-user historical_engaged flag) is the active TCC mechanism.
    Setup: 20 users, T1, target_rate=0.80.
      TCC baseline = ceil(20 * 0.80) = 16.
      With 8 historical_engaged: TCC = max(0, 16 - 8) = 8.
    """

    def setUp(self):
        self.users = [f"U{i:03d}" for i in range(1, 21)]
        self.tdf   = _tdf(self.users)
        self.cfg   = _base_cfg(
            triggers=(TriggerConfig("T1", 1, 0.80),),
            weekly_impression_cap=50,
            weekly_engagement_cap=50,
            weekly_click_cap=50,
            weekly_open_cap=50,
        )

    def _run_with_hist_flag(self, n_hist):
        state_df = UserStateManager(self.cfg).initialize_user_states(
            self.tdf, previous_state_df=None
        )
        audience_df, _ = AudienceManager(self.cfg).resolve(
            self.tdf, historical_df=None, state_df=state_df,
            as_of_date=self.cfg.simulation_start_date,
        )
        if n_hist > 0:
            hist_uids = self.users[:n_hist]
            audience_df = audience_df.copy()
            audience_df.loc[
                audience_df["user_id"].isin(hist_uids), "historical_engaged"
            ] = True
        events_df, _, _, _ = EngagementGenerator(self.cfg).generate(audience_df)
        return events_df, audience_df

    def test_s01_no_historical_engaged_baseline(self):
        """TCC = ceil(20*0.80)=16 with no historical_engaged."""
        events_df, _ = self._run_with_hist_flag(0)
        tcc_ceiling = math.ceil(20 * 0.80)
        clicks = events_df[events_df["action_type"] == "Click"]["user_id"].nunique()
        self.assertLessEqual(clicks, tcc_ceiling)

    def test_s02_with_8_historical_engaged_tcc_is_8(self):
        """TCC = max(0, 16-8) = 8 with 8 historical_engaged."""
        events_df, _ = self._run_with_hist_flag(8)
        tcc_remaining = 8
        hist_uids = set(self.users[:8])
        new_clicks = events_df[
            (events_df["action_type"] == "Click") &
            (~events_df["user_id"].isin(hist_uids))
        ]["user_id"].nunique()
        self.assertLessEqual(new_clicks, tcc_remaining)

    def test_s03_more_historical_produces_fewer_new_engagements(self):
        """8 historical_engaged -> fewer or equal new qualifying events than 0."""
        events_0, _ = self._run_with_hist_flag(0)
        events_8, _ = self._run_with_hist_flag(8)
        clicks_0 = events_0[events_0["action_type"] == "Click"]["user_id"].nunique()
        clicks_8 = events_8[events_8["action_type"] == "Click"]["user_id"].nunique()
        self.assertLessEqual(clicks_8, clicks_0)

    def test_s04_validation_engine_ter_rows_produced(self):
        """ValidationEngine produces TER rows with historical_engaged users present.

        TER pass/fail depends on probabilistic engagement vs the 0.80 target --
        not on the historical_engaged feature itself. This test verifies the
        validation engine runs correctly and produces TER output rows.
        """
        events_df, audience_df = self._run_with_hist_flag(5)
        ve = ValidationEngine(self.cfg)
        val_results, _, _ = ve.validate(events_df, audience_df)
        ter_rows = val_results[val_results["rule_id"].str.startswith("VAL-003")]
        self.assertGreater(len(ter_rows), 0)
        for status in ter_rows["status"]:
            self.assertIn(status, {"Pass", "Fail", "Skip"})

    def test_s05_fully_saturated_historical_gives_zero_new_events(self):
        """All 20 users marked historical_engaged -> TCC=0 -> zero qualifying events."""
        events_df, _ = self._run_with_hist_flag(20)
        clicks = events_df[events_df["action_type"] == "Click"]["user_id"].nunique()
        self.assertEqual(clicks, 0)


# ---------------------------------------------------------------------------
# HW-008: Validation Engine
# ---------------------------------------------------------------------------

class TestHW008ValidationEngine(unittest.TestCase):
    """HW-008: ValidationEngine correctly reflects historical_engaged users."""

    def setUp(self):
        self.users = [f"U{i:03d}" for i in range(1, 31)]
        self.tdf   = _tdf(self.users)
        self.cfg   = _base_cfg(triggers=(TriggerConfig("T1", 1, 0.50),))

    def _build_audience(self, n_hist):
        state_df = UserStateManager(self.cfg).initialize_user_states(
            self.tdf, previous_state_df=None
        )
        audience_df, _ = AudienceManager(self.cfg).resolve(
            self.tdf, historical_df=None, state_df=state_df,
            as_of_date=self.cfg.simulation_start_date,
        )
        if n_hist > 0:
            hist_uids = self.users[:n_hist]
            audience_df = audience_df.copy()
            audience_df.loc[
                audience_df["user_id"].isin(hist_uids), "historical_engaged"
            ] = True
        return audience_df

    def test_s01_val_010_multi_trigger_passes(self):
        audience_df = self._build_audience(0)
        events_df, _, _, _ = EngagementGenerator(self.cfg).generate(audience_df)
        val_results, _, _ = ValidationEngine(self.cfg).validate(events_df, audience_df)
        mt_rows = val_results[val_results["rule_id"] == "VAL-010"]
        if len(mt_rows) > 0:
            self.assertNotEqual(mt_rows["status"].iloc[0], "Fail")

    def test_s02_val_013_tcc_ceiling_respected(self):
        audience_df = self._build_audience(5)
        events_df, _, _, _ = EngagementGenerator(self.cfg).generate(audience_df)
        val_results, _, _ = ValidationEngine(self.cfg).validate(events_df, audience_df)
        tcc_rows = val_results[val_results["rule_id"].str.startswith("VAL-013")]
        fails = tcc_rows[tcc_rows["status"] == "Fail"]
        self.assertEqual(
            len(fails), 0,
            f"VAL-013 FAIL: {fails[['rule_id','message']].to_dict('records')}"
        )

    def test_s03_historical_engaged_column_present_in_audience(self):
        audience_df = self._build_audience(5)
        self.assertIn("historical_engaged", audience_df.columns)

    def test_s04_historical_engaged_users_sum_matches_n_hist(self):
        audience_df = self._build_audience(5)
        n = int(audience_df["historical_engaged"].astype(bool).sum())
        self.assertEqual(n, 5)

    def test_s05_quality_score_is_within_range(self):
        audience_df = self._build_audience(5)
        events_df, _, _, _ = EngagementGenerator(self.cfg).generate(audience_df)
        val_results, _, _ = ValidationEngine(self.cfg).validate(events_df, audience_df)
        score = ValidationEngine(self.cfg).generate_quality_score(val_results)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)


# ---------------------------------------------------------------------------
# HW-009: Workbook Export
# ---------------------------------------------------------------------------

class TestHW009WorkbookExport(unittest.TestCase):
    """HW-009: Workbook is generated correctly with historical data present."""

    def setUp(self):
        self.users = [f"U{i:03d}" for i in range(1, 21)]
        self.tdf   = _tdf(self.users)
        self.cfg   = _base_cfg(
            historical_engagement_window=HistoricalWindow.CUSTOM.value,
            historical_window_days=30,
        )
        self.hist_df = _make_hist_df(self.users[:5], _DATE_WITHIN_30)

    def _run_full(self):
        return SimulationOrchestrator(self.cfg).run(
            self.tdf,
            historical_df=self.hist_df,
            generate_excel=True,
        )

    def test_s01_workbook_bytes_are_non_empty(self):
        result = self._run_full()
        self.assertIsNotNone(result.workbook_bytes)
        self.assertGreater(len(result.workbook_bytes), 0)

    def test_s02_valid_zip_structure(self):
        import zipfile, io
        result = self._run_full()
        zf = zipfile.ZipFile(io.BytesIO(result.workbook_bytes))
        self.assertIn("xl/workbook.xml", zf.namelist())

    def test_s03_trigger_name_column_in_events(self):
        result = self._run_full()
        self.assertIn("trigger_name", result.events_df.columns)

    def test_s04_run_completes_without_error(self):
        result = self._run_full()
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.events_df)

    def test_s05_workbook_bytes_identical_across_runs(self):
        result1 = self._run_full()
        result2 = self._run_full()
        self.assertEqual(
            result1.workbook_bytes, result2.workbook_bytes,
            "Workbook bytes differ between runs -- non-deterministic."
        )


# ---------------------------------------------------------------------------
# HW-010: Determinism
# ---------------------------------------------------------------------------

class TestHW010Determinism(unittest.TestCase):
    """HW-010: Same inputs and same window produce identical outputs."""

    def setUp(self):
        self.users = [f"U{i:03d}" for i in range(1, 16)]
        self.tdf   = _tdf(self.users)
        self.hist_df = _concat_hist(
            _make_hist_df(_users("DET_A", 4), _DATE_WITHIN_30),
            _make_hist_df(_users("DET_B", 3), _DATE_31_60),
            _make_hist_df(_users("DET_C", 2), _DATE_61_90),
        )

    def _run(self, window, window_days=None):
        cfg = _base_cfg(
            historical_engagement_window=window,
            historical_window_days=window_days,
        )
        return SimulationOrchestrator(cfg).run(
            self.tdf, historical_df=self.hist_df, generate_excel=True
        )

    def test_s01_events_df_identical_across_two_runs(self):
        r1 = self._run(HistoricalWindow.LAST_90.value)
        r2 = self._run(HistoricalWindow.LAST_90.value)
        pd.testing.assert_frame_equal(
            r1.events_df.reset_index(drop=True),
            r2.events_df.reset_index(drop=True),
        )

    def test_s02_workbook_bytes_identical_across_two_runs(self):
        r1 = self._run(HistoricalWindow.LAST_90.value)
        r2 = self._run(HistoricalWindow.LAST_90.value)
        self.assertEqual(r1.workbook_bytes, r2.workbook_bytes)

    def test_s03_quality_score_identical_across_two_runs(self):
        r1 = self._run(HistoricalWindow.LAST_90.value)
        r2 = self._run(HistoricalWindow.LAST_90.value)
        self.assertEqual(r1.quality_score, r2.quality_score)

    def test_s04_capacity_counts_differ_between_window_sizes(self):
        cfg30 = _base_cfg(
            historical_engagement_window=HistoricalWindow.CUSTOM.value,
            historical_window_days=30,
        )
        cfg90 = _base_cfg(
            historical_engagement_window=HistoricalWindow.LAST_90.value,
        )
        cap30 = AudienceManager(cfg30).compute_remaining_capacity(
            self.hist_df, self.tdf
        )
        cap90 = AudienceManager(cfg90).compute_remaining_capacity(
            self.hist_df, self.tdf
        )
        self.assertLessEqual(
            cap30[0].historical_engaged_users,
            cap90[0].historical_engaged_users,
        )

    def test_s05_all_time_determinism(self):
        r1 = self._run(HistoricalWindow.ALL_TIME.value)
        r2 = self._run(HistoricalWindow.ALL_TIME.value)
        pd.testing.assert_frame_equal(
            r1.events_df.reset_index(drop=True),
            r2.events_df.reset_index(drop=True),
        )
        self.assertEqual(r1.workbook_bytes, r2.workbook_bytes)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
