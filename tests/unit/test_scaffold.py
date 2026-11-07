from kltn import __version__
from kltn.cli import main
from kltn.contracts import PredictionStatus


def test_version_is_present():
    assert __version__ == "0.1.0"


def test_prediction_status_keeps_errors_separate():
    assert PredictionStatus.ERROR.value == "error"
    assert PredictionStatus.INCONCLUSIVE.value == "inconclusive"


def test_cli_help(capsys):
    assert main([]) == 0
    assert "static" in capsys.readouterr().out.lower()
