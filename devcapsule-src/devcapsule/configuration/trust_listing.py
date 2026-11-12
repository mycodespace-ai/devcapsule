"""What ``project config trust list`` shows: each channel of a checkout against the home's trust record.

Pure: the command reads the lock and the home, and prints. The rows are
also the ``channels`` array of the command's JSON document, so their keys
are a stable interface.
"""

from __future__ import annotations

from typing import Any, Mapping

from .trust import Channel, HomeTrust

__all__ = ["render_trust_rows", "trust_rows"]


def trust_rows(channels: Mapping[str, Channel], trust: HomeTrust) -> list[dict[str, Any]]:
    """One row per channel of the checkout's lock, then one per accepted channel that the lock does not use.

    ``trusted`` says whether the home's acceptance covers the channel as the
    lock names it now. ``accepted`` is the home's entry for the channel, or
    None: a channel that is accepted and not trusted has left what was
    accepted, by a new origin, other terms or another integrity method.
    """
    rows: list[dict[str, Any]] = [
        {"channel": channel.id, "vendor": channel.vendor, "product": channel.product,
         "origins": list(channel.origins), "terms-url": channel.terms_url,
         "integrity": channel.integrity, "accepted": trust.channels.get(channel.id),
         "trusted": trust.covers(channel), "note": channel.note} for channel in channels.values()]
    for channel_id, entry in trust.channels.items():
        if channel_id not in channels:
            rows.append({"channel": channel_id, "vendor": entry["vendor"], "product": "", "origins": entry["origins"],
                         "terms-url": entry["terms-url"], "integrity": entry["integrity"], "accepted": entry,
                         "trusted": bool(entry["integrity"]), "note": "not used by this checkout"})
    return rows


def render_trust_rows(rows: list[dict[str, Any]]) -> list[str]:
    """The lines of the listing: a channel's state and channel, what was accepted when that no longer covers it, its note."""
    lines: list[str] = []
    for row in rows:
        state = "trusted" if row["trusted"] else ("not covered" if row["accepted"] else "not yet")
        origins = ", ".join(str(item) for item in row["origins"]) or "the lock"
        terms = f"; terms {row['terms-url']}" if row["terms-url"] else ""
        lines.append(f"{row['channel']:<18} {state:<11} {row['vendor']} — {row['product'] or '(not used by this checkout)'}; "
                     f"from {origins}; integrity {row['integrity'] or 'not recorded'}{terms}")
        if row["accepted"] and not row["trusted"]:
            entry = row["accepted"]
            lines.append(f"{'':<18} Accepted origins: {', '.join(entry['origins'])}; "
                         f"integrity {entry['integrity'] or 'not recorded'}; terms {entry['terms-url'] or 'none'}")
        if row["note"]:
            lines.append(f"{'':<18} {row['note']}")
    return lines
