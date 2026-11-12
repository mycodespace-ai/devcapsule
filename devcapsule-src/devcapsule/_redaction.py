"""Deterministic redaction of known credentials in diagnostic snapshots and exports.

Diagnostics scrub URL run tokens, console cookies, authentication headers,
secret-bearing CLI flags, and inline environment values while keeping paths,
ports, component names, and error messages readable. Arbitrary application
output can still carry project content or unlabelled secrets; callers state
that boundary explicitly rather than promising universal redaction.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Sequence

from devcapsule.docker_arguments import redact_environment

REDACTED = "<redacted>"

_QUERY_TOKEN_RE = re.compile(r"([?&]token=)[^&\s\"'#<>]+", re.IGNORECASE)
_ENCODED_QUERY_TOKEN_RE = re.compile(
    r"((?:(?:%3[fF]|%26)|(?<![A-Za-z0-9_-]))token%3[dD])[^&\s\"'#<>]+",
    re.IGNORECASE,
)
_CONSOLE_COOKIE_RE = re.compile(
    r"(devcapsule-console-token(?:-[A-Za-z0-9_-]+)?=)[^;\s\"'<>]+",
    re.IGNORECASE,
)
_AUTH_HEADER_RE = re.compile(
    r"(?im)((?<![A-Za-z0-9_-])(?:Authorization|Proxy-Authorization|Cookie|Set-Cookie|X-DevCapsule-Token)[ \t]*:[ \t]*)[^\r\n\"']+",
)
_SECRET_FLAG_INLINE_RE = re.compile(
    r"(--(?:token|password|passwd|secret|api-key|apikey|access-token)=)\S+",
    re.IGNORECASE,
)
_SECRET_BARE_FLAGS = frozenset({
    "--token",
    "--password",
    "--passwd",
    "--secret",
    "--api-key",
    "--apikey",
    "--access-token",
})
_NON_SECRET_ENV_SUFFIXES = (
    "_FILE",
    "_PATH",
    "_DIR",
    "_DIRECTORY",
    "_ENV",
    "_USERNAME",
    "_USER",
    "_HOSTS",
    "_HOST",
    "_PORT",
    "_URL",
)
_SECRET_ENV_NAME_RE = re.compile(
    r"^(?!XAUTHORITY$)[A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|PASSWD|API_KEY|APIKEY|PRIVATE_KEY|CREDENTIAL)[A-Z0-9_]*$",
    re.IGNORECASE,
)
_INLINE_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?<![A-Za-z0-9_-])([A-Za-z_][A-Za-z0-9_]*)=(\"[^\"]*\"|'[^']*'|[^\s\"'&;]+)",
    re.IGNORECASE,
)
_ENV_ASSIGNMENT_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", re.DOTALL)


def is_sensitive_env_name(name: str, extra_names: set[str] | None = None) -> bool:
    if extra_names and name in extra_names:
        return True
    upper = name.upper()
    if upper.endswith(_NON_SECRET_ENV_SUFFIXES):
        return False
    return _SECRET_ENV_NAME_RE.match(name) is not None


def _replace_inline_assignment(match: re.Match[str], env_names: set[str] | None) -> str:
    key, value = match.group(1), match.group(2)
    if value == REDACTED or not is_sensitive_env_name(key, env_names):
        return match.group(0)
    return f"{key}={REDACTED}"


def redact_text(
    text: str,
    *,
    secrets_to_scrub: Iterable[str] = (),
    env_names: set[str] | None = None,
) -> str:
    """Scrub known token, header, cookie, and secret patterns from ``text``."""

    if not text:
        return text
    result = text
    for secret in sorted({item for item in secrets_to_scrub if len(item) >= 8}, key=len, reverse=True):
        if secret in result:
            result = result.replace(secret, REDACTED)
    result = _QUERY_TOKEN_RE.sub(rf"\1{REDACTED}", result)
    result = _ENCODED_QUERY_TOKEN_RE.sub(rf"\1{REDACTED}", result)
    result = _CONSOLE_COOKIE_RE.sub(rf"\1{REDACTED}", result)
    result = _AUTH_HEADER_RE.sub(rf"\1{REDACTED}", result)
    result = _SECRET_FLAG_INLINE_RE.sub(rf"\1{REDACTED}", result)
    result = _INLINE_SECRET_ASSIGNMENT_RE.sub(
        lambda match: _replace_inline_assignment(match, env_names), result
    )
    return result


def redact_argv(
    argv: Sequence[str],
    *,
    secrets_to_scrub: Iterable[str] = (),
    env_names: set[str] | None = None,
) -> list[str]:
    """Redact inline environment options, secret flags, and token URLs in an argv vector."""

    masked = redact_environment(argv, names=None)
    result: list[str] = []
    skip_next = False
    for index, token in enumerate(masked):
        if skip_next:
            result.append(REDACTED)
            skip_next = False
            continue
        if token.lower() in _SECRET_BARE_FLAGS and index + 1 < len(masked):
            result.append(token)
            skip_next = True
            continue
        assignment = _ENV_ASSIGNMENT_RE.match(token)
        if assignment is not None:
            key, value = assignment.group(1), assignment.group(2)
            if value != REDACTED and is_sensitive_env_name(key, env_names):
                result.append(f"{key}={REDACTED}")
                continue
        result.append(redact_text(token, secrets_to_scrub=secrets_to_scrub, env_names=env_names))
    return result


def redact_json_value(
    value: Any,
    *,
    secrets_to_scrub: Iterable[str] = (),
    env_names: set[str] | None = None,
) -> Any:
    """Recursively apply :func:`redact_text` across JSON-compatible structures."""

    if isinstance(value, str):
        return redact_text(value, secrets_to_scrub=secrets_to_scrub, env_names=env_names)
    if isinstance(value, dict):
        return {
            redact_text(str(key), secrets_to_scrub=secrets_to_scrub, env_names=env_names): (
                REDACTED
                if isinstance(item, (str, list, tuple, dict)) and (
                    is_sensitive_env_name(str(key), env_names)
                    or str(key).lower() in {"authorization", "proxy-authorization", "cookie", "set-cookie", "x-devcapsule-token"}
                )
                else redact_json_value(item, secrets_to_scrub=secrets_to_scrub, env_names=env_names)
            )
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [
            redact_json_value(item, secrets_to_scrub=secrets_to_scrub, env_names=env_names)
            for item in value
        ]
    return value
