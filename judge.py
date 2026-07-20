"""Compatibility wrapper for the V2 attention engine.

The old `FocusJudge` implementation is preserved by the `v0.1-prototype` tag.
Use `onf_v2.core.attention_engine.AttentionEngine` for new development.
"""

from onf_v2.core.attention_engine import AttentionEngine
from onf_v2.core.face_analyzer import FaceAnalyzer


FocusJudge = AttentionEngine

__all__ = ["AttentionEngine", "FaceAnalyzer", "FocusJudge"]

