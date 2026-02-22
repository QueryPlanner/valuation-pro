"""
Valuation Engine
================

Pure FCFF "Simple Ginzu" valuation engine with zero external dependencies.

Public API:
- ``GinzuInputs`` / ``GinzuOutputs`` — data contracts
- ``compute_ginzu(inputs)`` — main valuation computation
- ``build_ginzu_inputs(data, assumptions)`` — canonical input preparation
- ``RnDCapitalizationInputs`` / ``compute_rnd_capitalization_adjustments``
- ``OptionInputs`` / ``compute_dilution_adjusted_black_scholes_option_value``
"""

from valuation_engine.engine import (
    FORECAST_YEARS,
    STABLE_TRANSITION_YEARS,
    GinzuInputs,
    GinzuOutputs,
    InputError,
    OptionInputs,
    RnDCapitalizationInputs,
    compute_dilution_adjusted_black_scholes_option_value,
    compute_ginzu,
    compute_rnd_capitalization_adjustments,
    normalize_to_float_list,
)
from valuation_engine.inputs_builder import build_ginzu_inputs

__all__ = [
    "FORECAST_YEARS",
    "STABLE_TRANSITION_YEARS",
    "GinzuInputs",
    "GinzuOutputs",
    "InputError",
    "OptionInputs",
    "RnDCapitalizationInputs",
    "build_ginzu_inputs",
    "compute_dilution_adjusted_black_scholes_option_value",
    "compute_ginzu",
    "compute_rnd_capitalization_adjustments",
    "normalize_to_float_list",
]
