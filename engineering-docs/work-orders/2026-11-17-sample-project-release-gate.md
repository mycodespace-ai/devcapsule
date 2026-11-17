# Exercise Sample Projects Before Releasing DevCapsule

Date: 2026-11-17
Status: ordered by the product owner
Owner: sample-projects, with presentations and maintenance
Source: project-management intake review, item 13; recorded in the
[coordination backlog](../wip/2026-08-09-project-management/coordination-backlog.md)

## Outcome

A new release exercises a maintained list of real sample projects through their
ordinary end-user paths. Each run produces evidence, including videos and a
presentation showing the capabilities exercised. Update the sample projects for
the new release as needed and record their tested revisions. The release driver
uses the results as a release acceptance check.

## Work

1. Sample-projects proposes the initial list of projects and a concrete end-to-end
   scenario for each, stating which DevCapsule capability it demonstrates. Check
   the samples' current locations; their former submodule arrangement is not an
   instruction to restore it.
2. Define pass/fail criteria, prerequisites and human-only steps before building
   the runner. Identify which candidate/artifact and project revisions are used.
3. Run through the normal user entry points with the candidate under acceptance;
   a source-only run does not prove the released executable works.
4. Reuse the presentations workstream's recording/authoring capability. Preserve
   a useful video/presentation and result for each selected sample, including
   failures. A recording is evidence to inspect, not by itself proof of success.
5. Sample updates are reviewable changes in the appropriate project repositories;
   follow their own workflow. Do not publish credentials or secret-bearing logs.
6. Maintenance adds the implemented check to the release procedure and retains
   the run results, candidate identity, sample revisions and evidence links in
   the release acceptance record.

## Decisions Still Needed In Design

The owner has ordered this work, not chosen a sample list, resource budget,
execution host or first enforcing release. Bring those choices together before
implementation. Explain how failing samples stop acceptance and how the owner
handles any exception. Do not silently waive the check or claim it already ran.
This work order does not itself add unimplemented machinery to the 0.3.1 gate.

## Acceptance

Demonstrate the check on an actual candidate using the agreed sample list;
retain the selected source/artifact revisions, results and viewable recordings
and presentations. Show that a failed required scenario is reported as failed,
not hidden by a successful recording step. The release guide must name the check
and point to its evidence. Product-owner acceptance settles the design and the
first release to which enforcement applies.
