# Architecture

![Modernisation Engine architecture](assets/modernisation-engine-architecture.png)

The diagram is a source-level view of the engine, not a deployment or release
claim. It shows the same domain service behind the Hermes CLI/tools and the
standalone Python CLI.

## Main paths

- **Assess**: source is copied/read without importing or executing it; inventory
  and identity snapshots produce a private, paged assessment.
- **Review**: strict contracts and owner-signed review records establish what
  should be preserved. A review record is not execution permission.
- **Prepare**: proposals and candidate copies are validated against the source
  and the reviewed contract.
- **Execute only by gate**: the signed executor and disposable rootless sandbox
  are unavailable unless trusted operator configuration and a fresh exact
  one-use grant are present. Archived grants and fixture signatures never
  authorise a live run.
- **Record and report**: observed outcomes, gaps, comparisons, rule traces and
  mutants are stored privately and rendered as bounded JSON, text or offline
  HTML.

## Trust boundaries

The private job store is outside source and candidate roots. Untrusted
repository code never runs during assessment. Execution uses a disposable,
network-disabled rootless container with no host home, credentials or Docker
socket. Owner signing keys remain outside the engine.

Source SVG: [modernisation-engine-architecture.svg](assets/modernisation-engine-architecture.svg).
