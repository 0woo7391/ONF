"""Compatibility exports for ONF V2.

The prototype configuration is preserved by the `v0.1-prototype` tag. New code
should import from `onf_v2.core.models` directly.
"""

from onf_v2.core.models import (  # noqa: F401
    AppState,
    CalibrationStatus,
    EffectiveState,
    Mode,
    ObservationState,
    MODE_THRESHOLDS,
)

