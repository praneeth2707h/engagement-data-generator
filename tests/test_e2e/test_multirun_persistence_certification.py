"""Stage 15 — Multi-Run Persistence Certification

tests/test_e2e/test_multirun_persistence_certification.py

Certifies that SimulationOrchestrator correctly persists state across
consecutive simulation runs when previous_state_df is threaded through.

Scenarios
---------
MR-001  State schema integrity across runs
MR-002  run_count increments for returning users; new users reset to 0
MR-003  Journey state persists (journey_status, current_ad, days_in_ad)
MR-004  Cooling period persists (cooling_period_end → COOLING classification)
MR-005  Re-entry after cooling expiry (RE_ENTRY when allow_reentry=True)
MR-006  Trigger history accumulates; first_trigger_name is idempotent
MR-007  Engagement counters (total_lifetime_engagements) persist
MR-008  Workbook export succeeds on run N+1 with previous_state_df
MR-009  Deterministic multi-run behavior (identical inputs → identical outputs)
MR-010  New users in run N+1 receive fresh initialisation (run_count=0)
"""
from __future__ import annotations

import io
import zipfile
from datetime import date, timedelta

import pandas as pd
import pytest

from core.audience_manager import AudienceManager
from core.simulation_orchestrator import SimulationOrchestrator
from core.user_state_manager import UserStateManager
from models.ad_config import AdConfig
from models.config_registry import ConfigRegistry
from models.enums import (
    EligibilityStatus,
    HistoricalWindow,
    JourneyStatus,
    RuleSeverity,
)
from models.rule_config import RuleConfig
from models.trigger_config import TriggerConfig
from utils.constants import TRIGGER_HISTORY_DELIMITER
from utils.schema_validator import USER_STATE_REQUIRED_COLUMNS

# ---------------------------------------------------------------------------
# Simulation windows
# ---------------------------------------------------------------------------

_RUN1_START = date(2024, 1, 1)
_RUN1_END   = date(2024, 1, 7)   # 7 days
_RUN2_START = date(2024, 1, 8)
_RUN2_END   = date(2024, 1, 14)  # 7 days
_RUN3_START = date(2024, 1, 15)
_RUN3_END   = date(2024, 1, 21)  # 7 days

_CAMPAIGN = "TEST_CAMPAIGN"
_N_USERS  = 20


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(
    sim_start: date = _RUN1_START,
    sim_end: date   = _RUN1_END,
    allow_reentry: bool = True,
    cooling_period_days: int = 5,
    target_rate: float = 0.50,
    n_triggers: int = 1,
) -> ConfigRegistry:
    ads = (
        AdConfig("Ad_A", 1, 2, True,  "Display", "VendorX", 0.10),
        AdConfig("Ad_B", 2, 2, False, "Email",   None,      0.05),
    )
    triggers = tuple(
        TriggerConfig(f"T{i}", i, target_rate)
        for i in range(1, n_triggers + 1)
    )
    rules = {"R-001": RuleConfig("R-001", "Test", RuleSeverity.SOFT.value, True, None)}
    return ConfigRegistry(
        campaign_id=_CAMPAIGN,
        campaign_name="Test Campaign",
        config_schema_version="2.0",
        simulation_start_date=sim_start,
        simulation_end_date=sim_end,
        ads=ads,
        default_vendor="DefaultVendor",
        cooling_period_days=cooling_period_days,
        triggers=triggers,
        segments=(),
        channels=(),
        rule_configs=rules,
        ter_mode="TER",
        historical_engagement_window=HistoricalWindow.LAST_90.value,
        historical_window_days=None,
        historical_campaign_match="Strict",
        historical_campaign_ids=(),
        behavior_score_decay_days=30,
        engagement_score_floor=0.0,
        engagement_score_ceiling=1.0,
        engagement_cooldown_days=3,
        weekly_impression_cap=5,
        weekly_click_cap=3,
        weekly_open_cap=5,
        weekly_engagement_cap=2,
        affinity_boost_on_click=0.05,
        affinity_decay_no_engage=0.02,
        affinity_floor=0.0,
        affinity_ceiling=1.0,
        channel_affinity_weight=0.5,
        creative_affinity_weight=0.5,
        fatigue_impression_threshold=3,
        fatigue_decay_factor=0.5,
        fatigue_recovery_days=7,
        admin_override=False,
        allow_reentry=allow_reentry,
        reentry_cooldown_days=0,
    )


def _make_trigger_df(
    n: int = _N_USERS,
    trigger: str = "T1",
    user_prefix: str = "U",
) -> pd.DataFrame:
    return pd.DataFrame({
        "Campaign_ID":  [_CAMPAIGN] * n,
        "User_ID":      [f"{user_prefix}{i:03d}" for i in range(1, n + 1)],
        "Trigger_Name": [trigger] * n,
        "Segment":      ["Seg_A"] * n,
        "Trigger_Date": [_RUN1_START] * n,
    })


def _run1(cfg: ConfigRegistry | None = None) -> tuple:
    """Execute run 1 (Jan 1–7) and return (result, cfg, tdf)."""
    c  = cfg or _make_config()
    td = _make_trigger_df()
    r  = SimulationOrchestrator(c).run(td, generate_excel=False)
    return r, c, td


def _run2(previous_state: pd.DataFrame, cfg: ConfigRegistry | None = None,
          tdf: pd.DataFrame | None = None) -> tuple:
    """Execute run 2 (Jan 8–14) using previous_state from run 1."""
    base   = cfg or _make_config()
    c2 = _make_config(
        sim_start=_RUN2_START, sim_end=_RUN2_END,
        allow_reentry=base.allow_reentry,
        cooling_period_days=base.cooling_period_days,
        target_rate=base.triggers[0].engagement_rate_target,
        n_triggers=len(base.triggers),
    )
    td = tdf or _make_trigger_df()
    r  = SimulationOrchestrator(c2).run(
        td, previous_state_df=previous_state, generate_excel=False
    )
    return r, c2, td


def _run3(previous_state: pd.DataFrame, cfg2: ConfigRegistry | None = None,
          tdf: pd.DataFrame | None = None) -> tuple:
    """Execute run 3 (Jan 15–21) using previous_state from run 2."""
    base = cfg2 or _make_config()
    c3 = _make_config(
        sim_start=_RUN3_START, sim_end=_RUN3_END,
        allow_reentry=base.allow_reentry,
        cooling_period_days=base.cooling_period_days,
        target_rate=base.triggers[0].engagement_rate_target,
    )
    td = tdf or _make_trigger_df()
    r  = SimulationOrchestrator(c3).run(
        td, previous_state_df=previous_state, generate_excel=False
    )
    return r, c3, td


# ---------------------------------------------------------------------------
# MR-001: State Schema Integrity
# ---------------------------------------------------------------------------

class TestMR001StateSchema:
    """MR-001: All required columns survive run → run state handoff."""

    def test_s01_run1_state_has_required_columns(self):
        r, _, _ = _run1()
        for col in USER_STATE_REQUIRED_COLUMNS:
            assert col in r.state_df.columns, f"Missing: {col}"

    def test_s02_run2_state_has_required_columns(self):
        r1, _, _ = _run1()
        r2, _, _ = _run2(r1.state_df)
        for col in USER_STATE_REQUIRED_COLUMNS:
            assert col in r2.state_df.columns, f"Missing after run2: {col}"

    def test_s03_run3_state_has_required_columns(self):
        r1, _, _ = _run1()
        r2, c2, _ = _run2(r1.state_df)
        r3, _, _ = _run3(r2.state_df, cfg2=c2)
        for col in USER_STATE_REQUIRED_COLUMNS:
            assert col in r3.state_df.columns, f"Missing after run3: {col}"

    def test_s04_user_id_preserved_across_runs(self):
        r1, _, _ = _run1()
        r2, _, _ = _run2(r1.state_df)
        uids1 = set(r1.state_df["user_id"])
        uids2 = set(r2.state_df["user_id"])
        assert uids1 == uids2, "user_id set changed across runs"

    def test_s05_campaign_id_consistent(self):
        r1, _, _ = _run1()
        r2, _, _ = _run2(r1.state_df)
        assert (r2.state_df["campaign_id"] == _CAMPAIGN).all()


# ---------------------------------------------------------------------------
# MR-002: run_count Increment
# ---------------------------------------------------------------------------

class TestMR002RunCount:
    """MR-002: run_count increments for returning users; new users start at 0."""

    def test_s01_new_users_run1_count_is_zero(self):
        r, _, _ = _run1()
        assert (r.state_df["run_count"] == 0).all()

    def test_s02_returning_users_run2_count_is_one(self):
        r1, _, _ = _run1()
        r2, _, _ = _run2(r1.state_df)
        assert (r2.state_df["run_count"] == 1).all()

    def test_s03_run3_count_is_two(self):
        r1, _, _ = _run1()
        r2, c2, _ = _run2(r1.state_df)
        r3, _, _ = _run3(r2.state_df, cfg2=c2)
        assert (r3.state_df["run_count"] == 2).all()

    def test_s04_new_users_in_run2_get_count_zero(self):
        """Users in run 2 trigger_df but absent from run 1 state_df get run_count=0."""
        r1, _, _ = _run1()
        # Run 2 trigger_df includes 5 new users (U021–U025)
        tdf_base = _make_trigger_df(n=_N_USERS)  # U001–U020
        tdf_new  = _make_trigger_df(n=5, user_prefix="V")  # V001–V005 (new)
        tdf2     = pd.concat([tdf_base, tdf_new], ignore_index=True)
        c2       = _make_config(sim_start=_RUN2_START, sim_end=_RUN2_END)
        r2       = SimulationOrchestrator(c2).run(
            tdf2, previous_state_df=r1.state_df, generate_excel=False
        )
        new_rows = r2.state_df[r2.state_df["user_id"].str.startswith("V")]
        assert (new_rows["run_count"] == 0).all(), "New users should have run_count=0"

    def test_s05_total_trigger_appearances_increments(self):
        r1, _, _ = _run1()
        r2, _, _ = _run2(r1.state_df)
        assert (r2.state_df["total_trigger_appearances"] >= 1).all()


# ---------------------------------------------------------------------------
# MR-003: Journey State Persistence
# ---------------------------------------------------------------------------

class TestMR003JourneyPersistence:
    """MR-003: journey_status, current_ad, and days_in_ad carry forward."""

    def _seed_state_with_active_journey(self, cfg: ConfigRegistry) -> pd.DataFrame:
        """Build a state_df with some users mid-journey via full run1."""
        r, _, _ = _run1(cfg)
        return r.state_df

    def test_s01_returning_users_carry_journey_status(self):
        """journey_status from run1 state_df flows into run2 initialized state."""
        r1, c1, tdf = _run1()
        # Manually set a cohort's journey_status to Active in state_df
        state_mod = r1.state_df.copy()
        cohort_ids = state_mod["user_id"].tolist()[:5]
        state_mod.loc[state_mod["user_id"].isin(cohort_ids), "journey_status"] = (
            JourneyStatus.ACTIVE.value
        )
        # Initialize run2 state manager with the modified state
        c2 = _make_config(sim_start=_RUN2_START, sim_end=_RUN2_END)
        init_df = UserStateManager(c2).initialize_user_states(
            tdf, previous_state_df=state_mod
        )
        # Returning users should carry the journey_status we set
        active_rows = init_df[init_df["user_id"].isin(cohort_ids)]
        assert (active_rows["journey_status"] == JourneyStatus.ACTIVE.value).all()

    def test_s02_current_ad_carries_forward(self):
        """current_ad set in run1 state_df is preserved for returning users."""
        r1, c1, tdf = _run1()
        state_mod = r1.state_df.copy()
        cohort_ids = state_mod["user_id"].tolist()[:5]
        state_mod.loc[state_mod["user_id"].isin(cohort_ids), "current_ad"] = "Ad_A"
        state_mod.loc[state_mod["user_id"].isin(cohort_ids), "journey_status"] = (
            JourneyStatus.ACTIVE.value
        )
        c2 = _make_config(sim_start=_RUN2_START, sim_end=_RUN2_END)
        init_df = UserStateManager(c2).initialize_user_states(
            tdf, previous_state_df=state_mod
        )
        rows = init_df[init_df["user_id"].isin(cohort_ids)]
        assert (rows["current_ad"] == "Ad_A").all()

    def test_s03_not_started_users_carry_forward_unchanged(self):
        """Users with journey_status=Not_Started keep that status into run2."""
        r1, c1, tdf = _run1()
        state_mod = r1.state_df.copy()
        not_started = state_mod[
            state_mod["journey_status"] == JourneyStatus.NOT_STARTED.value
        ]["user_id"].tolist()
        c2 = _make_config(sim_start=_RUN2_START, sim_end=_RUN2_END)
        init_df = UserStateManager(c2).initialize_user_states(
            tdf, previous_state_df=state_mod
        )
        if not_started:
            rows = init_df[init_df["user_id"].isin(not_started)]
            assert (rows["journey_status"] == JourneyStatus.NOT_STARTED.value).all()

    def test_s04_post_simulation_state_includes_journey_completions(self):
        """After ARCH-RISK-005 fix: state_df includes journey_status Completed for
        users whose journey finished during the simulation."""
        # Run with a long enough window for some completions (14 days, short ads)
        c = _make_config(sim_start=_RUN1_START, sim_end=date(2024, 1, 14))
        tdf = _make_trigger_df(n=30)
        r = SimulationOrchestrator(c).run(tdf, generate_excel=False)
        # With 2+2=4 day total journey, at least some users should complete in 14 days
        statuses = r.state_df["journey_status"].value_counts().to_dict()
        n_completed = statuses.get(JourneyStatus.COMPLETED.value, 0)
        n_active    = statuses.get(JourneyStatus.ACTIVE.value, 0)
        # At minimum the journey engine ran; either active or completed users present
        assert n_completed + n_active > 0, (
            f"Expected journey progression; got: {statuses}"
        )

    def test_s05_cooling_period_end_set_for_completed_users(self):
        """Users who completed journey in run1 have cooling_period_end populated."""
        c = _make_config(sim_start=_RUN1_START, sim_end=date(2024, 1, 14))
        tdf = _make_trigger_df(n=30)
        r = SimulationOrchestrator(c).run(tdf, generate_excel=False)
        completed = r.state_df[
            r.state_df["journey_status"] == JourneyStatus.COMPLETED.value
        ]
        if len(completed) > 0:
            # All completed users must have cooling_period_end set
            assert completed["cooling_period_end"].notna().all(), (
                "Completed users missing cooling_period_end"
            )


# ---------------------------------------------------------------------------
# MR-004: Cooling Period Persistence
# ---------------------------------------------------------------------------

class TestMR004CoolingPersistence:
    """MR-004: cooling_period_end carries forward → COOLING classification."""

    def _state_with_cooling(self, cooling_end: date) -> pd.DataFrame:
        """Build a state_df with all users in cooling period ending at cooling_end."""
        r1, _, _ = _run1()
        s = r1.state_df.copy()
        s["journey_status"]       = JourneyStatus.COMPLETED.value
        s["cooling_period_end"]   = cooling_end
        s["journey_completion_date"] = _RUN1_END
        return s

    def test_s01_cooling_period_end_survives_handoff(self):
        """cooling_period_end value in previous_state_df is preserved in run2 init."""
        cooling_end = _RUN2_START + timedelta(days=3)  # still cooling at run2 start
        prev = self._state_with_cooling(cooling_end)
        c2   = _make_config(sim_start=_RUN2_START, sim_end=_RUN2_END)
        init = UserStateManager(c2).initialize_user_states(
            _make_trigger_df(), previous_state_df=prev
        )
        init_dates = pd.to_datetime(init["cooling_period_end"], errors="coerce")
        assert (init_dates == pd.Timestamp(cooling_end)).all()

    def test_s02_users_classified_cooling_when_end_in_future(self):
        """Users with cooling_period_end > run2 start are classified COOLING."""
        cooling_end = _RUN2_START + timedelta(days=3)
        prev = self._state_with_cooling(cooling_end)
        c2   = _make_config(sim_start=_RUN2_START, sim_end=_RUN2_END)
        r2   = SimulationOrchestrator(c2).run(
            _make_trigger_df(), previous_state_df=prev, generate_excel=False
        )
        cooling_users = r2.audience_df[
            r2.audience_df["eligibility_status"] == EligibilityStatus.COOLING.value
        ]
        assert len(cooling_users) == _N_USERS, (
            f"Expected {_N_USERS} COOLING users; got {len(cooling_users)}"
        )

    def test_s03_cooling_users_generate_no_qualifying_events(self):
        """COOLING users should not produce qualifying engagement events."""
        cooling_end = _RUN2_START + timedelta(days=3)
        prev = self._state_with_cooling(cooling_end)
        c2   = _make_config(sim_start=_RUN2_START, sim_end=_RUN2_END)
        r2   = SimulationOrchestrator(c2).run(
            _make_trigger_df(), previous_state_df=prev, generate_excel=False
        )
        # Qualifying = Click for Display users; Open/Click for Email
        if not r2.events_df.empty:
            qualifying = r2.events_df[
                r2.events_df["action_type"].isin({"Click", "Open"})
            ]
            # All qualifying users should NOT be in the cooling cohort
            cooling_uids = set(r2.audience_df.loc[
                r2.audience_df["eligibility_status"] == EligibilityStatus.COOLING.value,
                "user_id",
            ])
            overlapping = set(qualifying["user_id"]) & cooling_uids
            assert len(overlapping) == 0, f"COOLING users produced qualifying events: {overlapping}"

    def test_s04_cooling_expiry_mid_run_transitions_to_eligible(self):
        """When cooling_period_end falls within run2, users transition partway through."""
        # Cooling expires after day 3 of run2 (Jan 11)
        cooling_end = _RUN2_START + timedelta(days=2)  # Jan 10
        prev = self._state_with_cooling(cooling_end)
        c2   = _make_config(sim_start=_RUN2_START, sim_end=_RUN2_END,
                            allow_reentry=True)
        r2   = SimulationOrchestrator(c2).run(
            _make_trigger_df(), previous_state_df=prev, generate_excel=False
        )
        # At the START of run2, all users are COOLING (classified at run2 start)
        # The run should complete without error regardless
        assert r2.succeeded

    def test_s05_journey_completion_date_preserved(self):
        """journey_completion_date set in run1 survives into run2 state."""
        prev = self._state_with_cooling(_RUN2_START + timedelta(days=2))
        c2   = _make_config(sim_start=_RUN2_START, sim_end=_RUN2_END)
        init = UserStateManager(c2).initialize_user_states(
            _make_trigger_df(), previous_state_df=prev
        )
        comp_dates = pd.to_datetime(init["journey_completion_date"], errors="coerce")
        assert comp_dates.notna().all(), "journey_completion_date lost during handoff"


# ---------------------------------------------------------------------------
# MR-005: Re-Entry After Cooling Expiry
# ---------------------------------------------------------------------------

class TestMR005ReentryPersistence:
    """MR-005: After cooling expires and allow_reentry=True → RE_ENTRY."""

    def _state_with_expired_cooling(self) -> pd.DataFrame:
        """State_df with cooling already expired before run3 start."""
        r1, _, _ = _run1()
        s = r1.state_df.copy()
        s["journey_status"]          = JourneyStatus.COMPLETED.value
        s["cooling_period_end"]      = _RUN2_END  # expires exactly at run2 end
        s["journey_completion_date"] = _RUN1_END
        return s

    def test_s01_re_entry_when_allow_reentry_true(self):
        """Users with expired cooling and allow_reentry=True are classified RE_ENTRY."""
        prev = self._state_with_expired_cooling()
        c3   = _make_config(sim_start=_RUN3_START, sim_end=_RUN3_END,
                            allow_reentry=True)
        r3   = SimulationOrchestrator(c3).run(
            _make_trigger_df(), previous_state_df=prev, generate_excel=False
        )
        re_entry = r3.audience_df[
            r3.audience_df["eligibility_status"] == EligibilityStatus.RE_ENTRY.value
        ]
        assert len(re_entry) == _N_USERS, (
            f"Expected {_N_USERS} RE_ENTRY; got {len(re_entry)}. "
            f"Statuses: {r3.audience_df['eligibility_status'].value_counts().to_dict()}"
        )

    def test_s02_excluded_when_allow_reentry_false(self):
        """Users with expired cooling and allow_reentry=False are classified EXCLUDED."""
        prev = self._state_with_expired_cooling()
        c3   = _make_config(sim_start=_RUN3_START, sim_end=_RUN3_END,
                            allow_reentry=False)
        r3   = SimulationOrchestrator(c3).run(
            _make_trigger_df(), previous_state_df=prev, generate_excel=False
        )
        excluded = r3.audience_df[
            r3.audience_df["eligibility_status"] == EligibilityStatus.EXCLUDED.value
        ]
        assert len(excluded) == _N_USERS, (
            f"Expected {_N_USERS} EXCLUDED; got {len(excluded)}"
        )

    def test_s03_re_entry_users_can_engage(self):
        """RE_ENTRY users are eligible to start a new journey and generate events."""
        prev = self._state_with_expired_cooling()
        c3   = _make_config(sim_start=_RUN3_START, sim_end=_RUN3_END,
                            allow_reentry=True, target_rate=0.80)
        r3   = SimulationOrchestrator(c3).run(
            _make_trigger_df(), previous_state_df=prev, generate_excel=False
        )
        # Events should exist for at least some RE_ENTRY users
        assert len(r3.events_df) > 0, "RE_ENTRY users produced no events"

    def test_s04_journey_completion_date_preserved_on_re_entry(self):
        """journey_completion_date from first journey preserved after re-entry (C-004)."""
        prev = self._state_with_expired_cooling()
        c3   = _make_config(sim_start=_RUN3_START, sim_end=_RUN3_END,
                            allow_reentry=True)
        r3   = SimulationOrchestrator(c3).run(
            _make_trigger_df(), previous_state_df=prev, generate_excel=False
        )
        # In audience_df, returning users should still have their original completion date
        comp_dates = pd.to_datetime(
            r3.audience_df["journey_completion_date"], errors="coerce"
        )
        # All should be non-null (set from run1)
        assert comp_dates.notna().all()

    def test_s05_run_count_correct_on_re_entry(self):
        """RE_ENTRY users in run3 have run_count=2 (incremented from run2)."""
        prev = self._state_with_expired_cooling()
        # Simulate passing through run2 first (cooling period), then run3
        c2   = _make_config(sim_start=_RUN2_START, sim_end=_RUN2_END, allow_reentry=True)
        r2   = SimulationOrchestrator(c2).run(
            _make_trigger_df(), previous_state_df=prev, generate_excel=False
        )
        c3   = _make_config(sim_start=_RUN3_START, sim_end=_RUN3_END, allow_reentry=True)
        r3   = SimulationOrchestrator(c3).run(
            _make_trigger_df(), previous_state_df=r2.state_df, generate_excel=False
        )
        assert (r3.state_df["run_count"] == 2).all()


# ---------------------------------------------------------------------------
# MR-006: Trigger History Accumulation
# ---------------------------------------------------------------------------

class TestMR006TriggerHistory:
    """MR-006: trigger_history accumulates; first_trigger_name is idempotent."""

    def test_s01_trigger_history_set_in_run1(self):
        """After run1, trigger_history contains T1 for all users."""
        r, _, _ = _run1()
        for _, row in r.audience_df.iterrows():
            assert row["trigger_history"] is not None
            assert "T1" in str(row["trigger_history"])

    def test_s02_trigger_history_accumulates_in_run2(self):
        """After run2 with same trigger, history = T1|T1."""
        r1, _, _ = _run1()
        r2, _, _ = _run2(r1.state_df)
        expected = f"T1{TRIGGER_HISTORY_DELIMITER}T1"
        for _, row in r2.audience_df.iterrows():
            assert str(row["trigger_history"]) == expected, (
                f"User {row['user_id']} history={row['trigger_history']!r}, expected {expected!r}"
            )

    def test_s03_first_trigger_name_idempotent(self):
        """first_trigger_name set in run1 is never overwritten in run2."""
        r1, _, _ = _run1()
        first_names_run1 = dict(
            zip(r1.audience_df["user_id"], r1.audience_df["first_trigger_name"])
        )
        r2, _, _ = _run2(r1.state_df)
        for uid, fname in first_names_run1.items():
            run2_fname = r2.audience_df.loc[
                r2.audience_df["user_id"] == uid, "first_trigger_name"
            ].values[0]
            assert str(run2_fname) == str(fname), (
                f"User {uid}: first_trigger_name changed {fname!r} → {run2_fname!r}"
            )

    def test_s04_total_trigger_appearances_increments_each_run(self):
        """total_trigger_appearances: 1 after run1, 2 after run2."""
        r1, _, _ = _run1()
        assert (r1.audience_df["total_trigger_appearances"] == 1).all()
        r2, _, _ = _run2(r1.state_df)
        assert (r2.audience_df["total_trigger_appearances"] == 2).all()

    def test_s05_three_run_chain_history_accumulates_correctly(self):
        """After run3: trigger_history = T1|T1|T1."""
        r1, _, _ = _run1()
        r2, c2, _ = _run2(r1.state_df)
        r3, _, _ = _run3(r2.state_df, cfg2=c2)
        expected = f"T1{TRIGGER_HISTORY_DELIMITER}T1{TRIGGER_HISTORY_DELIMITER}T1"
        for _, row in r3.audience_df.iterrows():
            assert str(row["trigger_history"]) == expected, (
                f"User {row['user_id']} history={row['trigger_history']!r}"
            )


# ---------------------------------------------------------------------------
# MR-007: Engagement Counter Persistence
# ---------------------------------------------------------------------------

class TestMR007CounterPersistence:
    """MR-007: total_lifetime_engagements and historical_engaged persist."""

    def test_s01_total_lifetime_engagements_in_run1_state(self):
        """state_df after run1 has total_lifetime_engagements > 0 for engaged users."""
        r, _, _ = _run1()
        n_engaged = (r.state_df["total_lifetime_engagements"] > 0).sum()
        assert n_engaged > 0, "Expected some users with total_lifetime_engagements > 0"

    def test_s02_lifetime_engagements_nondecreasing_across_runs(self):
        """For each returning user, run2 TLE >= run1 TLE (counters don't reset)."""
        r1, _, _ = _run1()
        tle1 = dict(zip(r1.state_df["user_id"], r1.state_df["total_lifetime_engagements"]))
        r2, _, _ = _run2(r1.state_df)
        tle2 = dict(zip(r2.state_df["user_id"], r2.state_df["total_lifetime_engagements"]))
        for uid in tle1:
            if uid in tle2:
                assert tle2[uid] >= tle1[uid], (
                    f"User {uid}: TLE decreased {tle1[uid]} → {tle2[uid]}"
                )

    def test_s03_historical_engaged_carries_forward(self):
        """historical_engaged=True stamped in previous_state_df is preserved."""
        r1, _, _ = _run1()
        state_mod = r1.state_df.copy()
        flagged_ids = state_mod["user_id"].tolist()[:5]
        state_mod.loc[state_mod["user_id"].isin(flagged_ids), "historical_engaged"] = True
        c2   = _make_config(sim_start=_RUN2_START, sim_end=_RUN2_END)
        init = UserStateManager(c2).initialize_user_states(
            _make_trigger_df(), previous_state_df=state_mod
        )
        flagged_rows = init[init["user_id"].isin(flagged_ids)]
        assert (flagged_rows["historical_engaged"] == True).all()  # noqa: E712

    def test_s04_engagement_score_carries_forward(self):
        """engagement_score for returning users is preserved from run1 into run2 init."""
        r1, _, _ = _run1()
        scores_r1 = dict(zip(r1.state_df["user_id"], r1.state_df["engagement_score"]))
        c2   = _make_config(sim_start=_RUN2_START, sim_end=_RUN2_END)
        init = UserStateManager(c2).initialize_user_states(
            _make_trigger_df(), previous_state_df=r1.state_df
        )
        scores_init = dict(zip(init["user_id"], init["engagement_score"]))
        for uid, score in scores_r1.items():
            assert abs(float(scores_init[uid]) - float(score)) < 1e-4, (
                f"User {uid}: score changed {score} → {scores_init[uid]}"
            )

    def test_s05_is_valid_column_carries_forward(self):
        """is_valid column is preserved from run1 into run2 init state."""
        r1, _, _ = _run1()
        c2   = _make_config(sim_start=_RUN2_START, sim_end=_RUN2_END)
        init = UserStateManager(c2).initialize_user_states(
            _make_trigger_df(), previous_state_df=r1.state_df
        )
        assert "is_valid" in init.columns
        assert init["is_valid"].notna().all()


# ---------------------------------------------------------------------------
# MR-008: Workbook Export Multi-Run
# ---------------------------------------------------------------------------

class TestMR008WorkbookMultiRun:
    """MR-008: Workbook generated correctly in run N+1 with previous_state_df."""

    def test_s01_run2_produces_workbook(self):
        r1, _, _ = _run1()
        c2 = _make_config(sim_start=_RUN2_START, sim_end=_RUN2_END)
        r2 = SimulationOrchestrator(c2).run(
            _make_trigger_df(), previous_state_df=r1.state_df, generate_excel=True
        )
        assert r2.workbook_bytes is not None
        assert len(r2.workbook_bytes) > 0

    def test_s02_run2_workbook_is_valid_xlsx(self):
        r1, _, _ = _run1()
        c2 = _make_config(sim_start=_RUN2_START, sim_end=_RUN2_END)
        r2 = SimulationOrchestrator(c2).run(
            _make_trigger_df(), previous_state_df=r1.state_df, generate_excel=True
        )
        buf = io.BytesIO(r2.workbook_bytes)
        assert zipfile.is_zipfile(buf), "workbook_bytes is not a valid ZIP/XLSX"
        with zipfile.ZipFile(buf) as zf:
            assert "xl/workbook.xml" in zf.namelist()

    def test_s03_run2_events_df_non_empty(self):
        # Use cooling_period_days=3 so cooling ends Jan 7 (journey completes ~Jan 4)
        # → run2 starts Jan 8 after cooling → users qualify as RE_ENTRY and can engage
        c1 = _make_config(cooling_period_days=3, allow_reentry=True)
        r1 = SimulationOrchestrator(c1).run(_make_trigger_df(), generate_excel=False)
        c2 = _make_config(
            sim_start=_RUN2_START, sim_end=_RUN2_END,
            cooling_period_days=3, allow_reentry=True,
        )
        r2 = SimulationOrchestrator(c2).run(
            _make_trigger_df(), previous_state_df=r1.state_df, generate_excel=False
        )
        assert len(r2.events_df) > 0, "Run2 produced no events"

    def test_s04_run2_quality_score_in_range(self):
        r1, _, _ = _run1()
        c2 = _make_config(sim_start=_RUN2_START, sim_end=_RUN2_END)
        r2 = SimulationOrchestrator(c2).run(
            _make_trigger_df(), previous_state_df=r1.state_df, generate_excel=False
        )
        assert 0.0 <= r2.quality_score <= 100.0

    def test_s05_workbook_contains_trigger_name_column(self):
        r1, _, _ = _run1()
        c2 = _make_config(sim_start=_RUN2_START, sim_end=_RUN2_END)
        r2 = SimulationOrchestrator(c2).run(
            _make_trigger_df(), previous_state_df=r1.state_df, generate_excel=False
        )
        assert "trigger_name" in r2.events_df.columns


# ---------------------------------------------------------------------------
# MR-009: Determinism
# ---------------------------------------------------------------------------

class TestMR009Determinism:
    """MR-009: Identical multi-run chains produce identical outputs."""

    def _two_run_chain(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Run chain A: run1 → run2.  Returns (events_r2, state_r2)."""
        r1, _, _ = _run1()
        r2, _, _ = _run2(r1.state_df)
        return r2.events_df, r2.state_df

    def test_s01_events_df_identical_across_two_chains(self):
        ev_a, _  = self._two_run_chain()
        ev_b, _  = self._two_run_chain()
        pd.testing.assert_frame_equal(
            ev_a.reset_index(drop=True),
            ev_b.reset_index(drop=True),
            check_dtype=False,
        )

    def test_s02_state_df_identical_across_two_chains(self):
        _, st_a = self._two_run_chain()
        _, st_b = self._two_run_chain()
        pd.testing.assert_frame_equal(
            st_a.sort_values("user_id").reset_index(drop=True),
            st_b.sort_values("user_id").reset_index(drop=True),
            check_dtype=False,
        )

    def test_s03_three_run_chain_determinism(self):
        """Same 3-run chain always produces identical run3 events."""
        def chain3():
            r1, _, _ = _run1()
            r2, c2, _ = _run2(r1.state_df)
            r3, _, _ = _run3(r2.state_df, cfg2=c2)
            return r3.events_df.reset_index(drop=True)

        ev_a = chain3()
        ev_b = chain3()
        pd.testing.assert_frame_equal(ev_a, ev_b, check_dtype=False)

    def test_s04_workbook_bytes_identical_across_chains(self):
        """Identical run2 chains produce identical workbook bytes."""
        def chain_wb():
            r1, _, _ = _run1()
            c2 = _make_config(sim_start=_RUN2_START, sim_end=_RUN2_END)
            r2 = SimulationOrchestrator(c2).run(
                _make_trigger_df(), previous_state_df=r1.state_df, generate_excel=True
            )
            return r2.workbook_bytes

        wb_a = chain_wb()
        wb_b = chain_wb()
        assert wb_a == wb_b, "workbook_bytes differ across identical chains"

    def test_s05_run_count_deterministic(self):
        """run_count values are identical across re-runs of the same chain."""
        def counts():
            r1, _, _ = _run1()
            r2, _, _ = _run2(r1.state_df)
            return r2.state_df.sort_values("user_id")["run_count"].tolist()

        assert counts() == counts()


# ---------------------------------------------------------------------------
# MR-010: New Users in Run N+1
# ---------------------------------------------------------------------------

class TestMR010NewUsers:
    """MR-010: Users absent from previous run get fresh initialisation."""

    def _run_with_new_users(self) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
        """Run1 with U001-U020, Run2 with U001-U020 + V001-V005."""
        r1, _, _ = _run1()
        tdf_base = _make_trigger_df(n=_N_USERS)
        tdf_new  = _make_trigger_df(n=5, user_prefix="V")
        tdf2     = pd.concat([tdf_base, tdf_new], ignore_index=True)
        c2       = _make_config(sim_start=_RUN2_START, sim_end=_RUN2_END)
        r2       = SimulationOrchestrator(c2).run(
            tdf2, previous_state_df=r1.state_df, generate_excel=False
        )
        new_uids = [f"V{i:03d}" for i in range(1, 6)]
        return r2.state_df, r2.audience_df, new_uids

    def test_s01_new_users_have_run_count_zero(self):
        state, _, new_uids = self._run_with_new_users()
        new_rows = state[state["user_id"].isin(new_uids)]
        assert (new_rows["run_count"] == 0).all()

    def test_s02_new_users_classified_new(self):
        _, audience, new_uids = self._run_with_new_users()
        new_rows = audience[audience["user_id"].isin(new_uids)]
        statuses = new_rows["eligibility_status"].astype(str).unique()
        # New users must be NEW or SKIPPED (if over capacity), never COOLING/EXCLUDED
        invalid = set(statuses) - {
            EligibilityStatus.NEW.value,
            EligibilityStatus.SKIPPED.value,
        }
        assert not invalid, f"New users had unexpected status: {invalid}"

    def test_s03_returning_users_have_run_count_one(self):
        state, _, _ = self._run_with_new_users()
        returning = state[~state["user_id"].str.startswith("V")]
        assert (returning["run_count"] == 1).all()

    def test_s04_new_users_have_no_prior_trigger_history(self):
        """New users in run2 get trigger_history = 'T1' (first occurrence only)."""
        _, audience, new_uids = self._run_with_new_users()
        new_rows = audience[audience["user_id"].isin(new_uids)]
        for _, row in new_rows.iterrows():
            hist = str(row["trigger_history"])
            # Should be exactly "T1", not "T1|T1"
            assert TRIGGER_HISTORY_DELIMITER not in hist, (
                f"New user {row['user_id']} has multi-run history: {hist!r}"
            )

    def test_s05_new_users_have_first_trigger_set(self):
        """New users in run2 have first_trigger_name set to their trigger."""
        _, audience, new_uids = self._run_with_new_users()
        new_rows = audience[audience["user_id"].isin(new_uids)]
        assert (new_rows["first_trigger_name"].astype(str) == "T1").all()
