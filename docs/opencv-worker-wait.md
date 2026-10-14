# Opt-in OpenCV worker waiting profile

This opt-in profile reduces active waiting in the bundled OpenCV pthread worker pool. It is environmental tuning, not a change to tracking calculations, and **not a fix for image jitter**. The maintained package ships it as an example only; the default driver service is unchanged and installation does not enable it.

The example contains only:

```ini
[Service]
Environment=OPENCV_THREAD_POOL_ACTIVE_WAIT_WORKER=0
```

The parameter is cached during OpenCV initialization. Changing a shell environment or reloading the unit does not change an already-running driver: activation and rollback require an explicit user-service restart, which interrupts XR output and may require recalibration. Main-thread waiting, thread count, tracking mode and rendering settings are not changed. This profile is relevant only when the actual SDK uses the OpenCV pthread pool and supports this parameter; it is not a universal recommendation for every device/backend.

## Evidence and latency tradeoff

A live VITURE Luma Ultra test measured seven worker threads using 62.6% of one logical CPU at baseline, 13.2% with this profile, and 58.2% after rollback. Those totals include useful work, not just spinning. The whole-process A/B was confounded by a different VIO workload after the final restart, so it does not establish preserved tracking quality or a universal CPU reduction. Image jitter was reported unchanged with the profile enabled.

An isolated benchmark of the actual vendor library used 32 unchanged threads and eight alternating pairs, validating every output element. Median process CPU fell from about 44.1% to 7.3% of one logical CPU, while the median of per-run p95 work durations rose from about 0.178 ms to 0.229 ms. These synthetic results show a CPU/latency tradeoff; they are not headset latency measurements and are not directly comparable to the laptop's worker counts or workload.

Validate translation as well as rotation, tracking latency, stale poses and long-session stability on your hardware. A fresh IMU timestamp, a completed calibration or a device position-capability flag alone does not establish equivalent working 6DoF. Roll back on tracking regressions, crashes, stale data or no useful CPU improvement.

## Enable manually

First inspect existing unit overrides; do not overwrite user-owned files:

```sh
systemctl --user show xr-driver.service -p FragmentPath -p DropInPaths -p Environment
```

Choose the example from the maintained Arch package, or from this source checkout:

```sh
profile=/usr/share/doc/xr-driver-git/examples/90-opencv-worker-no-spin.conf
# From a source checkout instead:
# profile=systemd/examples/90-opencv-worker-no-spin.conf

dropin="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/xr-driver.service.d/90-opencv-worker-no-spin.conf"
mkdir -p "$(dirname "$dropin")"
if test -e "$dropin"; then
    printf 'Existing override left unchanged: %s\n' "$dropin" >&2
else
    install -m644 "$profile" "$dropin" &&
    systemctl --user daemon-reload &&
    systemctl --user restart xr-driver.service
fi
systemctl --user show xr-driver.service -p DropInPaths -p Environment
```

This manual configuration survives reboot. It is not performed by package installation. If your pacman `NoExtract` rules omit `usr/share/doc/*`, use the source-checkout example instead or explicitly allow this package's documentation during installation. Other drop-ins can override the same variable; inspect the effective environment before comparing results. Also account for any separately created runtime override under `$XDG_RUNTIME_DIR/systemd/user/`, which disappears at reboot but may remain in effect during a persistent-profile test.

## Disable manually

Using the same `profile` and `dropin` paths from the enable section, remove only an unchanged copy of this example:

```sh
if cmp -s "$profile" "$dropin"; then
    rm -- "$dropin" &&
    systemctl --user daemon-reload &&
    systemctl --user restart xr-driver.service
else
    printf 'Override absent or edited; inspect it manually: %s\n' "$dropin" >&2
fi
systemctl --user show xr-driver.service -p DropInPaths -p Environment
```

Removing this file does not remove other persistent or runtime overrides. Do not use `systemctl revert` or delete an entire drop-in directory to undo this one profile. Recheck tracking and the actual workload after rollback, not only service readiness.
