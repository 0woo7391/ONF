"""Compatibility wrapper for ONF V2 session recording.

The prototype CSV logger is preserved by the `v0.1-prototype` tag. V2 records
raw decisions, events, summaries, and result images through SessionRecorder.
"""

from onf_v2.app.session_recorder import SessionRecorder


FocusLogger = SessionRecorder

__all__ = ["SessionRecorder", "FocusLogger"]

