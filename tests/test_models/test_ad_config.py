"""Tests for models/ad_config.py — MT-007."""
import pytest
from models.ad_config import AdConfig


def make_ad(**kwargs) -> AdConfig:
    defaults = dict(
        ad_name="Ad_A",
        ad_order=1,
        duration_days=7,
        move_on_click=True,
        channel="Email",
        vendor=None,
        target_ctr=0.05,
    )
    defaults.update(kwargs)
    return AdConfig(**defaults)


# ---------------------------------------------------------------------------
# Existing channel helper tests (MT-007)
# ---------------------------------------------------------------------------

def test_is_email_channel_true():
    assert make_ad(channel="Email").is_email_channel() is True


def test_is_email_channel_false():
    assert make_ad(channel="Display").is_email_channel() is False


def test_is_whatsapp_channel_true():
    assert make_ad(channel="WhatsApp").is_whatsapp_channel() is True


def test_is_whatsapp_channel_false():
    assert make_ad(channel="Email").is_whatsapp_channel() is False


# ---------------------------------------------------------------------------
# is_display_channel
# ---------------------------------------------------------------------------

def test_is_display_channel_display():
    assert make_ad(channel="Display").is_display_channel() is True


def test_is_display_channel_endemic():
    assert make_ad(channel="Endemic_Display").is_display_channel() is True


def test_is_display_channel_programmatic():
    assert make_ad(channel="Programmatic_Display").is_display_channel() is True


def test_is_display_channel_banner():
    assert make_ad(channel="Banner").is_display_channel() is True


def test_is_display_channel_email_false():
    assert make_ad(channel="Email").is_display_channel() is False


def test_is_display_channel_whatsapp_false():
    assert make_ad(channel="WhatsApp").is_display_channel() is False


# ---------------------------------------------------------------------------
# creative_affinity_column
# ---------------------------------------------------------------------------

def test_creative_affinity_column():
    assert make_ad(ad_name="Ad_X").creative_affinity_column() == "Creative_Affinity_Ad_X"


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

def test_ad_config_basic_construction():
    ad = make_ad()
    assert ad.ad_name == "Ad_A"
    assert ad.ad_order == 1
    assert ad.duration_days == 7
    assert ad.move_on_click is True
    assert ad.vendor is None
    assert ad.target_ctr == 0.05


def test_ad_config_with_vendor():
    ad = make_ad(vendor="VendorX")
    assert ad.vendor == "VendorX"
