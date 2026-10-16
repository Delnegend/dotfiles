# Sunshine & KMS Streaming

Sunshine game stream host configuration and recovery on Bazzite (KDE Plasma 6, Wayland, AMD Radeon GPU).

## Architecture

- **Systemd unit:** `dot_config/systemd/user/sunshine.service` binds to `graphical-session.target` (`PartOf=` and `WantedBy=`), orders after `xdg-desktop-autostart.target` and `xdg-desktop-portal.service`, delays 2 seconds (`ExecStartPre=/bin/sleep 2`), and includes fallback `Environment=WAYLAND_DISPLAY=wayland-0` and `DISPLAY=:0`.
- **Capture backend:** `~/.config/sunshine/sunshine.conf` sets `capture = kms` for direct GPU framebuffer capture from `/dev/dri/card1`.
- **Permissions:** Requires `cap_sys_admin+ep` on `/home/linuxbrew/.linuxbrew/Cellar/sunshine/<version>/bin/sunshine` so the DRM worker thread can read scanout buffers.

## Troubleshooting: Black Screen / Empty KMS Monitor List

### Symptoms

1. Moonlight connects but displays a solid black screen.
2. Sunshine logs show an empty monitor list and fails:
   ```text
   Info: -------- Start of KMS monitor list --------
   Info: --------- End of KMS monitor list ---------
   Fatal: Unable to find display or encoder during startup.
   ```
3. `kscreen-doctor` reports: `applying config failed! The session is not active`.
4. KWin logs report: `Unknown object '/org/freedesktop/login1/session/...'`.

### Cause

The display compositor (`kwin_wayland`) lost its `systemd-logind` seat assignment (commonly after restarting `plasmalogin` or a display manager crash). When logind revokes hardware access from an orphaned compositor, the graphics driver suspends display scanout (`fb_id = 0`), leaving no active hardware framebuffer for KMS to capture.

### Recovery

Terminate the user session to release orphaned processes and let logind allocate a clean seat with full hardware DRM master:

```bash
loginctl terminate-user lava
```

*(Alternatively, reboot the machine: `sudo reboot`).*
