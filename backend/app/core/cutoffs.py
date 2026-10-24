"""Day-ahead decision gates. These are market assumptions, not Elexon fields."""

from __future__ import annotations

from datetime import time

PROFILES: dict[str, dict[str, object]] = {
    "epex_60min": {
        "label": "09:20 UK time, day before delivery",
        "time": time(9, 20),
        "citation": (
            "Default deadline: 09:20 UK time on the day before delivery. "
            "The score uses the newest forecast already published by then. "
            "09:20 is the published close of the EPEX GB 60-minute day-ahead auction; "
            "Foregate uses that clock time only as a deadline, not as an auction result."
        ),
    },
    "nordpool_60min": {
        "label": "09:50 UK time, day before delivery",
        "time": time(9, 50),
        "citation": (
            "Deadline: 09:50 UK time on the day before delivery. "
            "This can include a newer forecast than the 09:20 deadline. "
            "09:50 is the Nord Pool N2EX day-ahead gate. "
            "A forecast published after 09:50 is not used in this score."
        ),
    },
    "epex_30min": {
        "label": "15:30 UK time, day before delivery",
        "time": time(15, 30),
        "citation": (
            "Deadline: 15:30 UK time on the day before delivery. "
            "This is later in the day, so a newer forecast may be included. "
            "15:30 is the published close of the EPEX GB 30-minute day-ahead auction. "
            "It is a deadline, not an instruction to trade that auction."
        ),
    },
}


def parse_hhmm(value: str) -> time:
    parts = value.strip().split(":")
    if len(parts) != 2:
        raise ValueError("cutoff_time must be HH:MM in UK local time")
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError as exc:
        raise ValueError("cutoff_time must be HH:MM in UK local time") from exc
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError("cutoff_time must be HH:MM in UK local time")
    return time(hour, minute)


def resolve_cutoff(profile: str, cutoff_time: str | None) -> tuple[str, str, time, str]:
    """Return profile id, label, UK local gate time, and citation."""
    if profile == "custom":
        if not cutoff_time:
            raise ValueError("cutoff_time is required when cutoff_profile is custom")
        clock = parse_hhmm(cutoff_time)
        label = f"Custom deadline {clock.strftime('%H:%M')} UK"
        citation = (
            f"Custom deadline: {clock.strftime('%H:%M')} UK time on the day before delivery. "
            "January 2026 is GMT, so this clock time matches UTC. "
            "The score uses the newest forecast already published by then, "
            "and leaves out anything published later."
        )
        return profile, label, clock, citation

    known = PROFILES.get(profile)
    if known is None:
        raise ValueError("cutoff_profile is not recognised")
    clock = parse_hhmm(cutoff_time) if cutoff_time else known["time"]
    assert isinstance(clock, time)
    return profile, str(known["label"]), clock, str(known["citation"])
