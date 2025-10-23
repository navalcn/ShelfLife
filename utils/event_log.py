from __future__ import annotations
import json
import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

UTC = timezone.utc


def _log_path(upload_folder: str) -> str:
    return os.path.join(upload_folder, 'event_log.json')


def log_event(upload_folder: str, *, item_id: int, prev_remaining: float, new_remaining: float) -> None:
    try:
        path = _log_path(upload_folder)
        os.makedirs(upload_folder, exist_ok=True)
        events: List[Dict[str, Any]] = []
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                events = json.load(f)
        events.append({
            't': datetime.now(UTC).isoformat(),
            'item_id': int(item_id),
            'prev_remaining': float(prev_remaining or 0),
            'new_remaining': float(new_remaining or 0),
        })
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
    except Exception:
        # best-effort logging; ignore failures
        pass


def compute_rolling_cpd(upload_folder: str, *, days: int = 14) -> Dict[int, float]:
    """
    Returns a dict of item_id -> estimated consumption_per_day based on
    observed decreases in remaining over the last `days`.
    """
    path = _log_path(upload_folder)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            events = json.load(f)
    except Exception:
        return {}
    cutoff = datetime.now(UTC) - timedelta(days=days)
    deltas: Dict[int, float] = {}
    for ev in events:
        try:
            t = datetime.fromisoformat(ev['t'])
            if t.tzinfo is None:
                t = t.replace(tzinfo=UTC)
            if t < cutoff:
                continue
            item_id = int(ev['item_id'])
            d = float(ev.get('prev_remaining', 0)) - float(ev.get('new_remaining', 0))
            if d > 0:
                deltas[item_id] = deltas.get(item_id, 0.0) + d
        except Exception:
            continue
    span_days = max(1, days)
    return {iid: round(val / span_days, 3) for iid, val in deltas.items() if val > 0}
