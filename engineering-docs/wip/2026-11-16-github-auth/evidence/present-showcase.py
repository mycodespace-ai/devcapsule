"""Present the retained SSH proxy run with the shared presentation producer.

Run from devcapsule-src with PYTHONPATH=. and pass the recording directory.
The recorded movie is not edited. Its hash binds the chapter timings to its bytes.
This is a producer for one retained interactive run, not a new E2E replay runner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from tests.e2e.scenario_presentation import parse_script, plan_presentation, write_presentation


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    own = Path(__file__).resolve().parent
    root = own.parents[3]
    timing = json.loads((own / "presentation-timing.json").read_text())
    evidence = args.evidence.resolve()
    movie = evidence / "scenario-video.webm"
    if hashlib.sha256(movie.read_bytes()).hexdigest() != timing["video_sha256"]:
        parser.error("The recording does not match these chapter timings; keep each run's timing with its movie.")
    result = json.loads((evidence / "result.json").read_text())
    if (result["status"], result["frames"], result["fps"]) != ("passed", timing["frames"], timing["fps"]):
        parser.error("The retained run must have passed with these frame counts and playback rate.")
    script = parse_script((root / "devcapsule-src/tests/e2e/scripts/github-ssh-proxy.md").read_text())
    chapters = timing["chapters"]
    for name in ["poster.png", *(chapter["screenshot"] for chapter in chapters)]:
        if not (evidence / name).is_file():
            parser.error(f"Missing recorded image: {name}")
    plan = plan_presentation({
        "id": "github-ssh-proxy",
        "title": "GitHub SSH: host identity, no copied keys",
        "description": "Clone from GitHub inside a fresh capsule using the outside launcher's SSH proxy. Check the credential boundary, see access fail without the socket, and restore normal access.",
        "actions": [
            {"reason": f"{index}. {chapter['caption']}", "caption": chapter["caption"]}
            for index, chapter in enumerate(chapters, start=1)
        ],
    }, script)
    document = plan.timed(
        [chapter["frames_after"] for chapter in chapters], timing["frames"], timing["fps"],
        video="scenario-video.webm", poster="poster.png",
        screenshots=[chapter["screenshot"] for chapter in chapters],
    )
    print(write_presentation(evidence, document))


if __name__ == "__main__":
    main()
