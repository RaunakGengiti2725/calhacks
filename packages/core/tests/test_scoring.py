"""Tests for success-probability scoring."""

from __future__ import annotations

from dryrun_core.models import StructureResult
from dryrun_core.scoring import (
    P_MAX,
    P_MIN,
    structure_term,
    success_probability,
)


def _structure(mean: float, plddt: list[float], misfold: bool = False) -> StructureResult:
    return StructureResult(
        design_id="d",
        pdb="",
        plddt=plddt,
        mean_plddt=mean,
        min_plddt=min(plddt) if plddt else 0.0,
        low_confidence_regions=[],
        misfold_flag=misfold,
    )


def test_probability_within_bounds() -> None:
    s = _structure(90.0, [90.0] * 50)
    p = success_probability(0.9, s)
    assert P_MIN <= p <= P_MAX


def test_higher_confidence_increases_probability() -> None:
    low = success_probability(0.7, _structure(50.0, [50.0] * 50))
    high = success_probability(0.7, _structure(95.0, [95.0] * 50))
    assert high > low


def test_higher_viability_increases_probability() -> None:
    s = _structure(85.0, [85.0] * 50)
    assert success_probability(0.9, s) > success_probability(0.4, s)


def test_misfold_flag_penalizes() -> None:
    plddt = [85.0] * 50
    clean = success_probability(0.8, _structure(85.0, plddt, misfold=False))
    flagged = success_probability(0.8, _structure(85.0, plddt, misfold=True))
    assert flagged < clean


def test_no_structure_is_discounted() -> None:
    s = _structure(85.0, [85.0] * 50)
    with_structure = success_probability(0.8, s)
    without = success_probability(0.8, None)
    assert without < with_structure


def test_disorder_lowers_structure_term() -> None:
    ordered = structure_term(_structure(80.0, [80.0] * 50))
    disordered = structure_term(_structure(80.0, [80.0] * 25 + [20.0] * 25))
    assert disordered < ordered
