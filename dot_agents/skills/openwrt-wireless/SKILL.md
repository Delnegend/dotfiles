---
name: openwrt-wireless
description: Use when configuring, auditing, or troubleshooting OpenWrt access points and Wi-Fi — UCI wireless/DAWN config, 802.11k/v/r steering, WPA2 vs WPA3, Apple/iOS/macOS client compatibility, mesh pitfalls, radio bring-up problems. Trigger on keywords OpenWrt, DAWN, 802.11r, 802.11k, 802.11v, roaming, steering, WPA3, sae, sae-mixed, mesh, 802.11s, batman, wifi reload, handle_probe_req, Channel 0, Apple WiFi.
---

# OpenWrt Wireless — hard rules for AP networks

Applies to OpenWrt 24.10/25.12+, hostapd + wpad-mbedtls, mac80211/mt76 APs
(MT7981/MT7986 filogic verified in production). Follow every rule literally;
deviations below are the exact failure modes seen in the wild.

## R1. Security: WPA2-PSK ONLY. No WPA3. Never `sae-mixed`.

- Use `encryption 'psk2'` (WPA2-AES, CCMP) on every SSID. End of story.
- **NEVER use `sae` (WPA3-only) or `sae-mixed`** on mixed-client networks:
  - `sae` excludes legacy and IoT devices (older iOS, Intel Macs, IoT).
  - `sae-mixed` causes common mixed-mode association failures across mobile and macOS clients.
  - 802.11r (FT) does not work with WPA3-SAE in hostapd (slow roaming only).
- If WPA3 is mandatory: use `sae+ccmp` and accept full-reauthentication roaming (no 802.11r).

## R2. Roaming: 802.11k + 802.11v + 802.11r ALL mandatory, every AP

Every `wifi-iface` (every SSID, every radio, every AP) gets:

```uci
config wifi-iface
	option device 'radio0'                # one per radio
	option mode 'ap'
	option ssid 'MYSSID'
	option network 'lan'
	option encryption 'psk2'              # R1: never sae / sae-mixed
	option key '<password>'
	option ieee80211k '1'                 # 802.11k neighbor/beacon reports
	option bss_transition '1'             # 802.11v BSS transition mgmt
	option ieee80211r '1'                 # 802.11r FT-PSK fast roaming
	option ft_over_ds '0'
	option ft_psk_generate_local '1'      # same SSID+PSK => same mobility domain
	option ieee80211w '1'                 # PMF optional — REQUIRED, or iOS
	                                      # ignores 802.11v BTM frames
	option max_inactivity '3600'          # hostapd default 300 kills sleeping
	                                      # iPhones ("zombie link")
	option dtim_period '2'
	option wpa_disable_eapol_key_retries '1'
```

Consequences of skipping any one of these (observed):
- no `ieee80211w` → BTM unprotected → iOS ignores steering → DAWN deauth-kicks.
- no `max_inactivity` → iOS standby devices deauthed after 5 min.
- no `ieee80211r` → no fast roaming (full 4-way handshake per handoff).

## R3. Mesh (802.11s / batman): FORBIDDEN on AP radios

- **Absolute rule: never configure a `mode 'mesh'` interface on any radio
  that also has AP VAPs.** Requires a dedicated radio (3+ band device) or a
  dedicated mesh-only device.
- Why: mesh and AP on the same radio causes AP VAPs to go off-air (`Channel: 0` in iwinfo, probe request failures).
- Prefer a **wired backhaul** (all APs on one L2 subnet). DAWN inter-AP
  discovery uses uMDNS over L2 and does NOT need mesh.
- If a mesh already exists on an AP radio: remove it. Cleanup = delete the
  `bat0` (`proto batadv`) and `batmesh` (`proto batadv_hardif`) sections from
  `/etc/config/network`, `uci commit network`, `/etc/init.d/network reload`.
  Then `wifi down && wifi up` to recover the AP VAPs.

## R4. DAWN — exact config (identical on every AP)

Only these values matter; everything else keep at defaults.

```uci
config metric 'global'
	option duration '150'                 # FORBIDDEN to be 0: clients refuse
	                                      # zero-length 802.11k beacon
	                                      # measurements -> DAWN blind to iOS
	option set_hostapd_nr '1'             # populate hostapd 802.11k neighbor
	                                      # DB; 0 (default) = empty Neighbor
	                                      # Reports -> iOS full-band scans on
	                                      # every roam (Apple uses first 6 NR
	                                      # entries; disassoc_nr_length 6
	                                      # default is correct)
	option kicking '3'
	option kicking_threshold '20'
	option min_number_to_kick '3'
	option rrm_mode 'pat'
	option eval_probe_req '0'
```

`config network`: keep defaults — TCP + uMDNS (`network_option '2'`),
`use_symm_enc '0'`. Never use broadcast/multicast modes (packet corruption
between APs); DAWN encryption is broken.

Apply: edit `/etc/config/dawn`, then `/etc/init.d/dawn restart` (client-safe).

## R5. Consistency: ALL APs identical, no exceptions

Same SSID, same `psk2` key, same k/v/r flags, same DAWN config on every AP.
802.11r mobility domain is auto-derived from SSID+key — must match.
DAWN `duration`/`set_hostapd_nr` must match, or steering data is asymmetric.

## R6. Change procedure (per AP, in order)

1. Backup: `cp /etc/config/<file> /etc/config/<file>.bak`
2. Edit via `uci set ...` / `uci delete ...`; `uci commit`
3. Apply:
   - wireless changes: `wifi down && wifi up` — **NEVER `wifi reload`**
     (reload triggers the R3 wedge on mesh radios; on pure-AP radios reload
     is acceptable but down/up is always safe)
   - DAWN-only: `/etc/init.d/dawn restart`
4. Verify on THIS AP:
   - `iwinfo | grep -e ESSID -e Channel` — every VAP shows a real channel
     (`1 (2.412 GHz)`, `36 (5.180 GHz)`). `Channel: 0` = VAP is dead. Fail
     here = R3/R6 violation.
   - `logread | grep handle_probe_req | tail` — must not grow after boot.
   - `ubus call network.wireless status` — `"up": true`, `"pending": false`.
   - `iwinfo <vap> assoclist` — clients associate.
5. Repeat on every AP; cross-check inter-AP steering both ways:
   `logread | grep dawn` shows `Remote PROBE` from the other AP's BSSIDs.

Recovery from the R3 wedge: `wifi down && wifi up` or reboot (restores boot
bring-up order). Do not re-run `wifi reload`.

## R7. Apple client facts (do not re-litigate)

- iOS roam trigger −70 dBm; candidate must be ≥8 dB stronger (active) /
  12 dB (idle). Intel Macs: −75 dBm, 12 dB.
- iOS prioritizes scan channels from the first 6 entries of the 802.11k
  Neighbor Report (R4 `set_hostapd_nr 1`).
- Intel Macs support NO 802.11k/r/v (PMKID only) — DAWN cannot BTM them,
  only deauth-kick. Apple-silicon Macs and iPhones support k/r/v.
- WPA3 on Intel Macs: documented failures (Catalina/Big Sur disconnects;
  Broadcom "hung-on-association" 2014–2017 MacBooks, Monterey/Big Sur) —
  device shows "Connecting…" forever. R1 avoids all of this.
- After switching an SSID's security, clients must forget and rejoin the
  network once.

## R8. Diagnostics cheat-sheet

- `iwinfo` / `iwinfo <vap> assoclist` — channels, clients
- `iw dev` — per-interface channel (absent = VAP off-air)
- `logread | grep dawn` — scoring/kicks (`kick: 1`, `deauth`, `BTM`)
- `logread | grep hostapd` — `deauthenticated due to inactivity`,
  `handle_probe_req: send failed`
- `ubus call network.wireless status` — radio/VAP state
- `/tmp/run/hostapd-phy*.conf` — generated hostapd config (per-phy)
- `uci get <pkg>.<section>.<option>` — persisted values

Windows shell gotcha: do not put pipes inside quoted SSH grep patterns
(PowerShell→ssh mangles them); use `grep -e a -e b` or `grep -c pattern file`.

