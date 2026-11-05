"""Prepare a reviewable acceptance record for a downloaded, smoke-tested candidate."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import urllib.request


def main() -> None:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("candidate")
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--accepted-by", required=True)
    parser.add_argument("--evidence", action="append", required=True)
    parser.add_argument("--repository", default="mycodespace-ai/devcapsule")
    args = parser.parse_args()
    match = re.fullmatch(r"(v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*))-rc(?:0|[1-9][0-9]*)", args.candidate)
    if not match or not re.fullmatch(r"[0-9a-f]{40}", args.baseline):
        parser.error("Use a candidate tag and a full baseline commit SHA")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repository):
        parser.error("Repository must be owner/name")
    base = f"https://github.com/{args.repository}/releases/download/{args.candidate}"
    with urllib.request.urlopen(base + "/release-manifest.json") as response:
        manifest = json.load(response)
    checksum = hashlib.sha256()
    with urllib.request.urlopen(base + "/devcapsule.pex") as response:
        while data := response.read(1024 * 1024):
            checksum.update(data)
    if manifest["tag"] != args.candidate or manifest["prerelease"] is not True or checksum.hexdigest() != manifest["artifacts"]["devcapsule.pex"]:
        raise ValueError("Downloaded candidate identity/checksum mismatch")
    tag = match[1]
    record = {"schema-version": 1, "tag": tag, "candidate-tag": args.candidate,
              "source-revision": manifest["source-revision"], "candidate-sha256": checksum.hexdigest(),
              "accepted-by": args.accepted_by, "evidence": args.evidence,
              "integration": {"method": "ancestry", "baseline": args.baseline}}
    path = Path(__file__).resolve().parents[2] / "engineering-docs" / "releases" / f"{tag}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        stream.write(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(f"Review and commit {path} on the integration branch; keep the candidate commit unchanged.")


if __name__ == "__main__":
    main()
