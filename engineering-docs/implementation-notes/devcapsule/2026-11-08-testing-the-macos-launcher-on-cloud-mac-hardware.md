# Testing The macOS Launcher On Cloud Mac Hardware, And The Alternatives

Written 2026-11-08 by Claude Code (Claude Fable 5.1) for `maintenance`, at
the owner's request, from a web survey of the same day. Prices and version
numbers are what the sources said that day; check them before allocating.

## Why real hardware

The macOS launcher of PR #338 runs on Apple silicon against Docker Desktop,
built from source as [the macOS guide](../../../docs/platforms/macos.md)
describes. Validating it means running Docker Desktop and capsules on a Mac,
not only building. Apple's license allows macOS only on Apple-branded
machines, so every cloud route is a physical Mac mini rented whole. Two
things follow:

- **Google Cloud has no offer.** It owns no Apple hardware. The only Google
  Cloud route found is a macOS guest nested inside an Intel machine type,
  which breaks Apple's license and is Intel, so it validates nothing about
  Apple silicon.
- **GitHub's hosted macOS runners cannot run Docker.** They are virtual
  machines on Apple silicon, and Apple's Virtualization framework gives a
  guest no nested virtualization, so neither Docker Desktop nor Colima can
  start its Linux VM there (`actions/runner-images#9254`). They can build
  the macOS launcher; they cannot run a capsule.

## Option A: AWS EC2 Mac, the recommended first run

EC2 Mac instances are bare-metal Mac minis on Dedicated Hosts without the
Nitro hypervisor, so Docker Desktop's Linux VM runs at the first level of
virtualization. AWS and Docker publish no statement about Docker on them; a
public runbook of 2026-10-29 on a `mac2.metal` running macOS 26.7 ran
Docker Desktop 4.97, Colima 0.10.3 (`vz`, `virtiofs`) and OrbStack through
a full check with no failures (`k-k1/agent-fleet#2961`). Treat our own first
run as the confirmation.

| Host | Hardware | On-Demand, N. Virginia | First day |
|---|---|---|---|
| `mac-m4.metal` | M4, 10 cores, 24 GiB | about $1.23 per host hour | about $30 |
| `mac-m4pro.metal` | M4 Pro, 14 cores, 48 GiB | about $1.97 per host hour | about $47 |
| `mac2-m2.metal` | M2, 8 cores, 24 GiB | about $0.88 per host hour | about $21 |

Rules that matter, from AWS's documentation:

- The Dedicated Host is the unit of billing, On-Demand only, per second
  after a **24-hour minimum allocation**, which AWS attributes to Apple's
  license. The host bills while the instance is stopped. Release it after
  24 hours, after stopping or terminating the instance; a scrubbing run
  follows.
- One instance per host. Launch takes 6 to 20 minutes. Boot is from an EBS
  volume; AWS recommends 10,000 IOPS and 400 MiB/s. The internal SSD is
  unsupported. Do not enable FileVault.
- M4 and M4 Pro hosts need macOS Sequoia 15.6 or later; Tahoe 26 images
  are published. Regions vary; check the instance-types-by-region table.
- Apple Intelligence is unavailable when booting from an external volume,
  which is irrelevant to us.

### Procedure, one validation day

1. Allocate the host and launch the latest Sequoia or Tahoe AMI with a
   key pair, an EBS root of 200 GB or more, and a security group that
   allows SSH from your address only.
2. Over SSH as `ec2-user`, set a password and enable Screen Sharing, then
   open a tunnel and connect with the Screen Sharing app (Finder, Go,
   Connect to Server, `vnc://localhost:5900`):

   ```bash
   ssh -i key.pem ec2-user@INSTANCE
   sudo passwd ec2-user
   sudo launchctl enable system/com.apple.screensharing
   sudo launchctl load -w /System/Library/LaunchDaemons/com.apple.screensharing.plist
   exit
   ssh -L 5900:localhost:5900 -i key.pem ec2-user@INSTANCE
   ```

   Amazon DCV also supports EC2 Mac since 2025-11-12, with audio and 60
   frames per second, if VNC proves too slow for IDE work. Sequoia asks to
   approve Local Network Privacy on first GUI login; approve it.
3. In the desktop session, install Docker Desktop and raise its disk limit
   under Settings, Resources. Docker Desktop's first start needs a
   logged-in screen session, so do this over VNC, not over SSH.
4. Follow the macOS guide's *Build and install* from a clean checkout of
   the release branch, or install the executables from option C below,
   then run the smoke below.
5. Record the evidence in the release overview, stop and terminate the
   instance, and release the host once 24 hours have passed.

## Option B: Scaleway Apple silicon, the cheaper second machine

Scaleway rents bare-metal Mac minis in Paris: M4-S (16 GB) at about €0.22
per hour or €149 per month, M2 Pro and M2 in PARIS 1, M1 in PARIS 3. The
same 24-hour minimum applies, for the same license reason; billing runs
until the Mac mini is deleted, and deletion takes about 30 minutes. Access
is SSH and VNC; the console's *Open remote desktop* button carries the
VNC credentials, the port is random and shown on the Overview page, and a
non-default macOS version adds about an hour to installation. Nobody was
found who ran Docker Desktop there; the hardware is the same kind of bare
metal, so expect the same result as AWS and treat the first run as the
test. One day costs about €5.30.

## Option C: build on hosted runners, run on the Mac

Building and running are separable. The macOS launcher is one
`scripts/build-pex.sh` invocation with `DEVCAPSULE_SCIE_PLATFORM=macos-aarch64`
and needs no Docker, so a hosted `macos-15` runner (Apple silicon) can
build it. The two Linux runtimes need Linux Python: hosted `ubuntu-24.04`
and `ubuntu-24.04-arm` runners build them natively, without the emulated
`docker run` of the guide. A `workflow_dispatch` workflow taking a ref,
building the three executables and uploading them as artifacts would let
anyone with a Mac validate a branch by downloading, installing as the guide
shows, and running. This is the shape a published macOS executable would
take if the owner rules one in; until then it is a validation aid, not a
release channel, and its artifacts carry `--allow-unpublished-revision`
semantics: the commit must be public, since a base build installs the web
console from it.

## Option D: a one-shot self-hosted runner on a friend's Mac

The owner's idea: a collaborator registers their own M4 Mac as a GitHub
Actions runner for one job that pulls `release-0.3.1`, builds the macOS
launcher and the runtimes, and runs the smoke against their Docker Desktop.
It works, with three rules:

- **Register the runner ephemeral** (`config.sh --ephemeral`), so it takes
  exactly one job and unregisters itself; remove it from the repository
  settings afterwards regardless.
- **The repository is public.** GitHub's own guidance is not to use
  self-hosted runners on public repositories, because a workflow from a
  fork can run on the machine. Restrict exposure: the job runs only on
  `workflow_dispatch` from a protected branch, the repository setting
  *Require approval for all outside collaborators* stays on, and the runner
  is labelled uniquely so no other workflow can target it by accident.
  Even so, the runner runs as the collaborator's user on their personal
  machine, and anything the checked-out branch's scripts do, it does. The
  collaborator should read the workflow and the branch before registering.
- **Docker Desktop must already be running** in the collaborator's logged-in
  session, with the disk limit raised; the runner inherits that session's
  Docker socket.

The collaborator may have built the launcher already: PR #338's author ran
the macOS guide's build on their own Mac. If they instead ran from source
with the launcher's own interpreter, the validation still needs the built
executables, because the runtime delivered into the capsule must be a PEX
of the same commit (R-RUNTIME-001), and the smoke below checks exactly that.

## The smoke, whichever machine

Record each line with its output in the release overview under
*Candidates*, with the macOS and Docker Desktop versions.

1. `devcapsule version --json` from an empty directory: version, build
   mnemonic and source revision match the branch commit; the runtimes in
   `DEVCAPSULE_RUNTIME_PEX` report the same version.
2. A fresh project: `devcapsule project init` with Enter for
   `linux-arm64`, then `project run`; the arm64 base pulls, the contained
   desktop opens in the browser, the IDE's main window appears. Time it.
3. The same project under emulation: delete the arm64 lock, `project run`;
   the amd64 base and IDE image build under emulation (about ten minutes
   for PyCharm on a 14-core Mac, per the guide); the IDE appears.
4. Eclipse on `linux-arm64` with an empty component cache, which also
   closes the libsoup bug for arm64 if the acquisition succeeds, and
   Eclipse under emulation with an empty cache, which is the amd64
   acquisition the 0.3.1 repin must prove.
5. `docker-daemon` authorized: from inside the capsule, `docker run` of a
   small image, which the guide says is the arm64 variant; confirm with
   `docker version`.
6. A `network host` project: the launch falls back to bridge with the
   warning the guide describes; the web console reaches `127.0.0.1`.
7. Stop, `project run` again, the session resumes; `devcapsule cleanup`
   leaves the Mac's Docker Desktop disk where it was before step 2, within
   the base images kept on purpose.

What a failure looks like is a bug record under `engineering-docs/bugs/`
with the Mac's hardware, macOS and Docker Desktop versions, and the
command's output, as the guide asks adopters to report.

## Sources

AWS: [EC2 Mac instances](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-mac-instances.html),
[FAQs](https://aws.amazon.com/ec2/instance-types/mac/faqs/),
[connect to a Mac instance](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/connect-to-mac-instance.html),
[macOS AMI release notes](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/macos-ami-overview.html),
[Amazon DCV on EC2 Mac](https://aws.amazon.com/about-aws/whats-new/2025/11/amazon-dcv-ed2-mac-instances),
[Dedicated Host pricing](https://aws.amazon.com/ec2/dedicated-hosts/pricing/) and a
[third-party reading of the price feed](https://macyou.co/blog/aws-ec2-mac-pricing-explained)
of 2026-09-25. Scaleway: [Apple silicon FAQ](https://github.com/scaleway/docs-content/blob/main/pages/apple-silicon/faq.mdx),
[quickstart](https://github.com/scaleway/docs-content/blob/main/pages/apple-silicon/quickstart.mdx),
[Mac mini M4](https://www.scaleway.com/en/mac-mini-m4/), and a
[price comparison](https://macswarm.com/compare/cloud-mac-pricing/) checked
2026-11-07. Docker on EC2 Mac: [a public runbook](https://github.com/k-k1/agent-fleet/issues/2961)
of 2026-10-29. Hosted runners: [actions/runner-images#9254](https://github.com/actions/runner-images/issues/9254);
Apple's statement that the Virtualization framework does not work inside a
VM: [developer forums](https://developer.apple.com/forums/thread/749809).
