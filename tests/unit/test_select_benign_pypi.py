"""Kiem tra cac ham loc thuan (khong goi mang) cua scripts/select_benign_pypi.py."""
import datetime as dt
import importlib.util
from pathlib import Path

_PATH = Path(__file__).resolve().parents[2] / "scripts" / "select_benign_pypi.py"
_spec = importlib.util.spec_from_file_location("select_benign_pypi", _PATH)
sbp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sbp)

UTC = dt.UTC
D_FROM = dt.datetime(2024, 1, 1, tzinfo=UTC)
D_TO = dt.datetime(2026, 5, 1, tzinfo=UTC)


def _file(kind, when, yanked=False):
    return {"packagetype": kind, "upload_time_iso_8601": when, "yanked": yanked,
            "filename": "x", "size": 10}


def test_normalize_pep503():
    assert sbp.normalize("Foo_Bar.baz") == "foo-bar-baz"
    assert sbp.normalize("requests") == "requests"


def test_bucket_thresholds():
    assert sbp.bucket_of(None) == "unknown"
    assert sbp.bucket_of(250_000) == "popular"
    assert sbp.bucket_of(5_000) == "medium"
    assert sbp.bucket_of(0) == "small"


def test_eligible_versions_filters_prerelease_yanked_wheel_only_and_window():
    doc = {"releases": {
        "1.0.0": [_file("sdist", "2024-06-01T00:00:00Z")],
        "1.1.0rc1": [_file("sdist", "2024-07-01T00:00:00Z")],
        "1.2.0": [_file("sdist", "2024-08-01T00:00:00Z", yanked=True)],
        "1.3.0": [_file("bdist_wheel", "2024-09-01T00:00:00Z")],
        "0.9.0": [_file("sdist", "2023-06-01T00:00:00Z")],
        "2.0.0": [_file("sdist", "2026-10-01T00:00:00Z")],
        "1.0.0.post1": [_file("sdist", "2024-06-02T00:00:00Z")],
    }}
    assert sbp.eligible_versions(doc, D_FROM, D_TO) == ["1.0.0", "1.0.0.post1"]


def test_repository_url():
    assert sbp.repository_url({"project_urls": {"Source": "https://github.com/a/b"}})
    assert sbp.repository_url({"home_page": "https://gitlab.com/a/b"})
    assert sbp.repository_url({"project_urls": {"Docs": "https://a.readthedocs.io"}}) == ""
    assert sbp.repository_url({"project_urls": None, "home_page": None}) == ""



def test_type_stub_packages_are_detected():
    assert sbp.is_type_stub("types-requests")
    assert sbp.is_type_stub("pandas-stubs")
    assert not sbp.is_type_stub("requests")
