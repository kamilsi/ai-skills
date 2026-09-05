---
name: macos-disk-triage
description: >-
  Diagnose and safely reclaim disk space on a space-constrained macOS machine
  (Apple Silicon, Xcode/iOS development). Use when the user reports a full or
  nearly-full disk, "low disk space", "no space left on device", a huge "System
  Data" / "Dane systemowe" category in Storage settings, a macOS update that
  will not install for lack of space, Xcode or simulator disk bloat, or asks
  whether files can be offloaded to a NAS or cloud. Starts from a known baseline
  and a catalogue of known culprits instead of scanning from scratch.
---

# macOS Disk Triage

A runbook for a **245 GB Apple Silicon MacBook used for iOS development**. It is chronically near-full. The space is consumed by developer tooling and macOS, **not** user data — so the fix is almost never "move files to the NAS".

## Rule Zero: look for a runaway writer before you analyse anything

Most "my disk is full" events on this machine are **not** accumulation. They are a process writing gigabytes per hour. Clearing caches without finding it wastes the session — the space refills within the hour.

```bash
bash ~/.gemini/skills/macos-disk-triage/scripts/disk-triage.sh
```

The script checks the known culprits first, then reports the real layout. It is **read-only and deletes nothing**. Takes 1–2 minutes (`du` over large trees) — run it once and read the whole report rather than re-running sections.

### Known culprit #1 — Gemini desktop app (confirmed 2026-09-05)

`~/Library/Caches/CCTClearcutLogger` is Google's Clearcut telemetry spool. Healthy size is **kilobytes**. On this machine it was measured writing **336 MB / 30 s (~39 GB/hour)**, rebuilding 11 GB in 35 minutes after a full wipe, with the app at 137% CPU.

Cause: `GIPPseudonymousIDStore pseudonymousIDWithoutCheckingEnabledStatus` fails with `NSCocoaErrorDomain`; the failure is logged as a telemetry event **carrying a 15-frame stack trace**; that write then fails (`CCTLogWriter flushInternal:`), generating another event. ~8,600 records/sec, no backoff. It is **intermittent** — a clean run does not mean it is fixed.

```bash
du -sh ~/Library/Caches/CCTClearcutLogger        # >50MB = active
bash ~/.gemini/skills/macos-disk-triage/scripts/disk-triage.sh rate ~/Library/Caches/CCTClearcutLogger
```

**Quit Gemini first.** The process holds the files open, so deleting while it runs frees nothing. Then `rm -rf ~/Library/Caches/CCTClearcutLogger`. Gemini has been removed from login items; if it reappears there, remove it again. Reported to Google 2026-09-05 (their ticket 387258074 was mis-triaged as a duplicate of Maps SDK bug 383595404).

**Generalise it:** any directory under `~/Library/Caches` above ~1 GB is a bug, not a cache. Find the writer with `lsof +D <dir>`.

## Measurement gotchas

- **`df -h /` lies.** It reports the sealed system volume (~15 GB). Real usage is `/System/Volumes/Data`, or `diskutil apfs list`.
- **`du` double-counts simulator runtimes.** Mounted runtime volumes appear under `/Library/Developer/CoreSimulator/Volumes` *and* as DMGs in `/System/Library/AssetsV2`. Only the DMGs are real bytes; trust `xcrun simctl runtime list`.
- **`kMDItemLastUsedDate` is unreliable.** It returns `(null)` for apps that are definitely in use (Xcode does). **Never delete an app based on it.**
- **Storage settings' "System Data" is meaningless** — it lumps AssetsV2, simulator DMGs, caches and swap together.

## Reclaim, ranked by durability

| Target | Frees | Durable? | Risk |
|---|---|---|---|
| Runaway cache (see Rule Zero) | 10–50 GB | Until it recurs | None |
| Unused simulator runtime — `xcrun simctl runtime delete "iOS X.Y"` | ~8 GB each | **Yes** | Keep the one you build against |
| Orphaned sim devices — `xcrun simctl delete unavailable` | ~2 GB | Yes | None |
| Simulator dyld cache `/Library/Developer/CoreSimulator/Caches/dyld` | ~9 GB | No — regrows | Slower first sim boot |
| `~/Library/Developer/Xcode/DerivedData` | GBs | No — regrows in days | None |
| `iOS DeviceSupport` | ~6 GB | No | Re-downloads on next device connect |
| Xcode `UserData/Previews` | ~2 GB | No | None |
| `brew cleanup` | ~0.6 GB | No | None |
| Orphaned app leftovers (`~/Library/<VendorApp>` with app uninstalled) | GBs | **Yes** | Verify the app is really gone |
| Other user accounts (`sudo du -sh /Users/*/`) | ~8 GB? | **Yes** | The one real NAS-archive candidate |
| Mail attachments / Messages in iCloud | 5–8 GB | Yes | Live app data — use the app's own setting |

Deleting the regrowing ones buys days, not a fix. The goal is a **30–40 GB working floor**, not a one-time number.

## Never do these

- **Never delete anything under `/System/Volumes/Preboot`.** It can make the Mac unbootable. ~12–18 GB there is normal on Apple Silicon (cryptexes carry ARM + x86 code).
- **Never `rm` a live cloud sync root** (`~/Library/CloudStorage/*`, Google Drive, OneDrive). Files there are usually **placeholders with no local copy**, and deleting propagates to the cloud. Unlink the account in the app instead. Check with `du -sh` — a "1.2 GB" folder showing 1.3 MB of usage is all placeholders.
- **Do not suggest disabling Apple Intelligence on this Mac.** It is blocked entirely because the system language is `pl_PL`; it was never on, there is nothing to reclaim. The 2.7 GB `UAF_Siri_Understanding` asset is ordinary Siri (set to English US), not AI.
- **Do not propose NAS/cloud offload as the primary fix.** Total offloadable user data here is ~3 GB — less than one simulator runtime. Verify with section 5 of the script before suggesting it.

## Baseline

Compare findings against [the 2026-09-05 forensic baseline](./references/baseline-2026-09-05.md) — full volume breakdown, what each block does, and what a healthy machine looks like.
