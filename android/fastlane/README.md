fastlane documentation
----

# Installation

Make sure you have the latest version of the Xcode command line tools installed:

```sh
xcode-select --install
```

For _fastlane_ installation instructions, see [Installing _fastlane_](https://docs.fastlane.tools/#installing-fastlane)

# Available Actions

## Android

### android validate

```sh
[bundle exec] fastlane android validate
```

Validate the release configuration. Needs no credentials and uploads nothing.

Options: rollout:0.1 also validates a staged-rollout fraction.

### android internal

```sh
[bundle exec] fastlane android internal
```

Build the signed release bundle (AAB) and upload it to the internal testing track.

Options: dry_run:true builds the bundle (signed only if signing env is present) and stops before Google Play.

### android production

```sh
[bundle exec] fastlane android production
```

Promote a versionCode from the internal track to production as a staged rollout.

Options: version_code:N rollout:0.1 (1 = full release) dry_run:true

### android rollout

```sh
[bundle exec] fastlane android rollout
```

Manage the production staged rollout: increase it, complete it (100%), or halt it.

Options: action:increase|complete|halt rollout:0.5 (required for increase/halt) dry_run:true

----

This README.md is auto-generated and will be re-generated every time [_fastlane_](https://fastlane.tools) is run.

More information about _fastlane_ can be found on [fastlane.tools](https://fastlane.tools).

The documentation of _fastlane_ can be found on [docs.fastlane.tools](https://docs.fastlane.tools).
