## Summary

<!-- What does this PR do? One sentence is enough for small changes. -->

## Changes

<!-- Bullet-point list of what changed and why. -->

## Testing

<!-- How was this tested? (unit tests, manual smoke test, simulator, device, …) -->

## Performance checklist

> Full guide, budgets, and profiling instructions:
> [docs/performance-guide.md](../docs/performance-guide.md). Answer these if your change
> could plausibly affect performance.

- [ ] No network, disk, or database I/O added on the main thread or in an initializer.
- [ ] Any new screen or network path is instrumented (`.trackScreen` / `TrackScreen`).
- [ ] No unbounded loop, collection growth, or retry without a cap.
- [ ] If a list or screen changed: it is lazy and keyed, derived collections are
      memoized, and it was checked on a device with 100+ items.
- [ ] **If this claims a speedup:** a before/after number is included, measured on a
      physical device in a release build, 3+ iterations, median or p95 reported. "Feels
      faster" is not a measurement.
- [ ] **If a threshold or baseline moved:** say so explicitly and justify it.

<!-- Answer "yes", "no — not applicable", or explain. Don't just delete a line. -->

## Parity checklist

> This project maintains a feature-parity table in [PARITY.md](../PARITY.md) that
> tracks which features are implemented on iOS vs Android. **Please answer the
> questions below before requesting review.**

- [ ] This PR **does not** add, change, or remove any user-facing feature on either
  platform — no PARITY.md update needed.

  **— OR —**

- [ ] This PR adds/changes/removes a user-facing feature. I have updated PARITY.md:
  - Updated the status symbol(s) for the affected row(s).
  - Added or updated "Notes" if the implementation is partial or has caveats.
  - Removed or updated any rows in the "Known gaps" table that this PR closes.

<!-- If you changed only one platform, call out the gap explicitly so it doesn't
     get lost. Example:
     > Implemented Withdraw on Android. iOS already has this (✅). Updated PARITY.md. -->

## Related issues

<!-- Closes #... -->
