"""Record real Playwright actions and derive presentation timing from their frames.

Public surface: ``Recording``. The caller supplies its page, scenario, evidence
directory and ffmpeg command. No DevCapsule installation or test harness is
needed by the exported package. Assertions belong in the supplied action.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
import json
from pathlib import Path
import subprocess
from typing import Any

from .producer import PresentationError, Script, plan_presentation, write_presentation

__all__ = ["Recording"]


class Recording:
    """Capture bursts around actions, excluding time the agent spends thinking.

    Each action has a one-based script step and a caption. Repeated actions may
    belong to the same step. Steps must run in order. ``finish`` keeps a failed
    or incomplete run visibly failed; it never infers success from screenshots.
    Use a new evidence directory for each attempt; existing runs are refused.
    """

    def __init__(
        self, evidence: Path, *, script: Script, scenario_id: str, title: str,
        summary: str, ffmpeg: Sequence[str],
    ) -> None:
        # Check the complete scenario before opening a browser or making files.
        scenario: dict[str, Any] = {"id": scenario_id, "title": title, "description": summary,
                    "actions": [{"reason": f"{n}. {step.action}"}
                                for n, step in enumerate(script.steps, 1)]}
        plan_presentation(scenario, script)
        if isinstance(ffmpeg, (str, bytes)) or not ffmpeg or not all(isinstance(part, str) and part for part in ffmpeg):
            raise PresentationError("supply the ffmpeg command from the browser-automation environment")
        evidence.mkdir(parents=True, exist_ok=False)
        self.evidence = evidence
        self.script = script
        self.scenario = scenario
        self.ffmpeg = tuple(ffmpeg)
        self.actions: list[dict[str, Any]] = []
        self.frames_after_actions: list[int] = []
        self.screenshots: list[str] = []
        self.frame_count = 0
        self.last_step = 0
        self.failure = ""
        self.finished = False
        self.frames = evidence / "frames.mjpeg"

    def _capture(self, page: Any, count: int) -> None:
        # Playwright's bundled ffmpeg decodes MJPEG, but need not decode PNG.
        with self.frames.open("ab") as output:
            for _ in range(count):
                output.write(page.screenshot(type="jpeg", quality=90))
                self.frame_count += 1
                page.wait_for_timeout(100)

    def action(self, page: Any, step: int, caption: str, perform: Callable[[], object]) -> None:
        """Record an action and its assertions; retain failure evidence and re-raise.

        The supplied callback uses ordinary Playwright selectors, mouse/keyboard
        operations or project checks. Keep actions small enough that their before
        and after frames show the interaction; native Playwright video may also be
        kept in ``evidence/raw`` to preserve uninterrupted motion.
        """
        if self.finished or self.failure:
            raise PresentationError("this run has finished or failed; start a new run")
        if (isinstance(step, bool) or not isinstance(step, int)
                or not 1 <= step <= len(self.script.steps)
                or step not in (self.last_step, self.last_step + 1)):
            raise PresentationError("actions must visit script steps in order, starting at 1")
        if not isinstance(caption, str) or not caption.strip():
            raise PresentationError("each recorded action needs a non-empty caption")
        self.last_step = step
        entry: dict[str, Any] = {"reason": f"{step}. {caption}", "status": "passed"}
        self.actions.append(entry)
        try:
            self._capture(page, 2)
            perform()
            self._capture(page, 6)
            screenshot = f"step-{len(self.actions):03d}.png"
            page.screenshot(path=str(self.evidence / screenshot))
            self.screenshots.append(screenshot)
        except BaseException as error:
            self.failure = f"{type(error).__name__}: {error}"
            entry.update(status="failed", error=self.failure)
            # A disconnected browser must not replace the original test failure.
            try:
                self._capture(page, 1)
                screenshot = f"step-{len(self.actions):03d}.png"
                page.screenshot(path=str(self.evidence / screenshot))
                self.screenshots.append(screenshot)
            except Exception:
                pass
            raise
        finally:
            self.frames_after_actions.append(self.frame_count)
            entry["frames_after"] = self.frame_count
            self._write_result()

    def _write_result(self) -> None:
        complete = self.last_step == len(self.script.steps) and not self.failure
        result = {"status": "failed" if self.failure else "passed" if self.finished and complete else "incomplete",
                  "error": self.failure, "steps_reached": self.last_step,
                  "steps_planned": len(self.script.steps)}
        for name, value in (("scenario-result.json", result), ("action-log.json", self.actions)):
            (self.evidence / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def finish(self) -> Path:
        """Encode frames and publish the deck last; refuse missing visual evidence.

        Logs survive encoding failure. A failed test produces a labelled deck
        containing only the steps it reached, and keeps its failed result.
        """
        if self.finished:
            raise PresentationError("this recording has already been finished")
        self.finished = True
        self._write_result()
        if not self.actions or len(self.screenshots) != len(self.actions):
            raise PresentationError("no complete visual evidence; inspect scenario-result.json and action-log.json")
        complete = self.last_step == len(self.script.steps) and not self.failure
        suffix = "" if complete else " (FAILED)" if self.failure else " (INCOMPLETE)"
        scenario = dict(self.scenario, title=self.scenario["title"].strip() + suffix, actions=self.actions)
        reached = Script(self.script.goal, self.script.stack, self.script.illustrates,
                         self.script.steps[:self.last_step])
        plan = plan_presentation(scenario, reached)
        document = plan.timed(self.frames_after_actions, self.frame_count, 12,
                              video="scenario-video.webm", poster="poster.png", screenshots=self.screenshots)
        video = self.evidence / "scenario-video.webm"
        with self.frames.open("rb") as frames, (self.evidence / "ffmpeg.log").open("wb") as log:
            subprocess.run(
                [*self.ffmpeg, "-y", "-f", "image2pipe", "-vcodec", "mjpeg", "-r", "12",
                 "-i", "pipe:0", "-c:v", "libvpx", "-b:v", "3M", "-crf", "10", str(video)],
                stdin=frames, stdout=log, stderr=log, check=True, timeout=120,
            )
        if not video.is_file() or video.stat().st_size == 0:
            raise PresentationError("video encoding produced no scenario-video.webm; inspect ffmpeg.log")
        (self.evidence / "poster.png").write_bytes((self.evidence / self.screenshots[0]).read_bytes())
        return write_presentation(self.evidence, document)
