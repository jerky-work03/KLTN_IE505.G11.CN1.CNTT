"""Shared values for datasets, detectors, CLI reports and evaluation."""

from enum import StrEnum


class Ecosystem(StrEnum):
    NPM = "npm"
    PYPI = "pypi"


class Label(StrEnum):
    MALICIOUS = "malicious"
    BENIGN = "benign"
    UNKNOWN = "unknown"


class PredictionStatus(StrEnum):
    MALICIOUS = "malicious"
    BENIGN = "benign"
    INCONCLUSIVE = "inconclusive"
    ERROR = "error"
    UNSUPPORTED = "unsupported"
