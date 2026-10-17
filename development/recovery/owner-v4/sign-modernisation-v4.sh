#!/usr/bin/env bash
# Sign the ONE Modernisation Engine v4 follow-up request. Run as YOURSELF (sahil).
# Your private key never leaves your account and is never printed or copied.
# The signature (not secret, one-use, bound to this exact test run) is saved to
# ~/modernisation-v4-signature.txt so KENSEI can pick it up.
set -euo pipefail

EXPIRES=1792441542
CANDIDATE_SHA=54a14a390443751d6b0f3e93f6374918fb091604001605d56cc5f6a40c5ac1f5
OUT="$HOME/modernisation-v4-signature.txt"
CANDIDATE_B64='eyJleHBpcmVzX2F0IjoxNzkyNDQxNTQyLCJtYXhfdXNlcyI6MSwibm9uY2UiOiIzNDk3YTdlN2JkNjM0NTQ5YTFkYWJhNWNkYzY5OTQ5YSIsIm9wZXJhdGlvbiI6eyJhY3RvciI6InNhaGlsIiwiYXJndiI6WyIvY2FuZGlkYXRlLy52ZW52L2Jpbi9weXRob24iLCItQiIsIi1jIiwiaW1wb3J0IGJhc2U2NCxoYXNobGliLGpzb24sc3lzLHhtbC5ldHJlZS5FbGVtZW50VHJlZSBhcyBFXG5pbXBvcnQgcHl0ZXN0XG5zdGF0dXM9aW50KHB5dGVzdC5tYWluKFsndGVzdHMvdW5pdC90ZXN0X2Rhc2hib2FyZF9hcGkucHknLCd0ZXN0cy9zZWN1cml0eS90ZXN0X3dzX2F1dGhfZmFpbHNfY2xvc2VkLnB5JywnLXAnLCdubzpjYWNoZXByb3ZpZGVyJywnLW8nLCdhZGRvcHRzPScsJy0tanVuaXR4bWw9L3RtcC93YWxraWUtcmVzdWx0LnhtbCcsJy1yYSddKSlcbnN5cy5zdGRvdXQuZmx1c2goKVxudHJ5OlxuICAgIHdpdGggb3BlbignL3RtcC93YWxraWUtcmVzdWx0LnhtbCcsJ3JiJykgYXMgc3RyZWFtOnJhdz1zdHJlYW0ucmVhZCgxMDQ4NTc3KVxuZXhjZXB0IE9TRXJyb3I6XG4gICAgcmF3PWInJ1xuY291bnRzPU5vbmVcbmlmIHJhdyBhbmQgbGVuKHJhdyk8PTEwNDg1NzY6XG4gICAgdHJ5OlxuICAgICAgICBub2Rlcz1saXN0KEUuZnJvbXN0cmluZyhyYXcpLml0ZXIoJ3Rlc3RjYXNlJykpXG4gICAgICAgIGNvdW50cz17J2NvbGxlY3RlZCc6bGVuKG5vZGVzKSwnZmFpbHVyZXMnOnN1bShuLmZpbmQoJ2ZhaWx1cmUnKSBpcyBub3QgTm9uZSBmb3IgbiBpbiBub2RlcyksJ2Vycm9ycyc6c3VtKG4uZmluZCgnZXJyb3InKSBpcyBub3QgTm9uZSBmb3IgbiBpbiBub2RlcyksJ3NraXBwZWQnOnN1bShuLmZpbmQoJ3NraXBwZWQnKSBpcyBub3QgTm9uZSBmb3IgbiBpbiBub2Rlcyl9XG4gICAgZXhjZXB0IEUuUGFyc2VFcnJvcjpcbiAgICAgICAgY291bnRzPU5vbmVcbnJhdz1yYXdbOjEwNDg1NzZdXG5wcmludCgnUlVOTkVSX1BZVEVTVF9TVEFUVVM9JytzdHIoc3RhdHVzKSlcbnByaW50KCdSVU5ORVJfQ09VTlRTX0pTT049Jytqc29uLmR1bXBzKGNvdW50cyxzb3J0X2tleXM9VHJ1ZSkpXG5wcmludCgnUlVOTkVSX0VOVl9KU09OPScranNvbi5kdW1wcyh7J3B5dGhvbic6c3lzLnZlcnNpb259KSlcbnByaW50KCdSVU5ORVJfSlVOSVRfQllURVM9JytzdHIobGVuKHJhdykpKVxucHJpbnQoJ1JVTk5FUl9KVU5JVF9TSEEyNTY9JytoYXNobGliLnNoYTI1NihyYXcpLmhleGRpZ2VzdCgpKVxucHJpbnQoJ1JVTk5FUl9KVU5JVF9CRUdJTicpXG5wcmludChiYXNlNjQuYjY0ZW5jb2RlKHJhdykuZGVjb2RlKCkpXG5wcmludCgnUlVOTkVSX0pVTklUX0VORCcsZmx1c2g9VHJ1ZSlcbnJhaXNlIFN5c3RlbUV4aXQoMCBpZiBzdGF0dXM9PTAgYW5kIGNvdW50cz09eydjb2xsZWN0ZWQnOjIwLCdmYWlsdXJlcyc6MCwnZXJyb3JzJzowLCdza2lwcGVkJzowfSBlbHNlIDIpXG4iXSwiYXR0ZW1wdF9pZCI6ImNhbmRpZGF0ZS1lYjA2MjViYTk5OGE0ZDdkOWNiNmM1ZTM0ZTQyNjk1ZCIsImNhbmRpZGF0ZV9kaWdlc3QiOiIyZTI0MzgyOWNhMjc3ZWRjNzMzY2ExYjU2ZDI5NThmYjIwMzU5ZjNjNmI0ZjQyNTU5Y2QyYzZiYzA4YjQyZjgzIiwiZW52aXJvbm1lbnRfZGlnZXN0IjoiMDE0ODdkZGViZjQxMDk3OTViOWRhZmQ0ZWZjZTlhMDFjN2ViZDYyZWNmY2U1YThiZjQyYzBmNWM5NjYwZTY0MiIsImltYWdlX2RpZ2VzdCI6ImIzNjEzZjFmNzJmMjA4MzQ5NjFmZWY1MjMwZmI4MDA1OWE2ZjRlZjZhYzg5NDY0YWYxNWJjMTNjZDk3OTViMjYiLCJqb2JfaWQiOiJ3YWxraWUtcHl0aG9uMzE0LWZhc3RhcGktdjQiLCJuZXR3b3JrIjoibm9uZSIsIm9yYWNsZV9kaWdlc3QiOiJjZmM5ZDk0ZWYzOGRlMWI3YTgwNTNmY2EzNDZmZjg2MWU2ZDgyM2M5MDg4NzdmYjQ1YmUyODI5MDg0ODkxMjc1Iiwib3V0cHV0X2xpbWl0X2J5dGVzIjo0MTk0MzA0LCJwcm9maWxlIjoiZGVmYXVsdCIsInJlYWRfcm9vdHMiOlsiL3NvdXJjZSJdLCJzY2hlbWFfdmVyc2lvbiI6MSwic291cmNlX2RpZ2VzdCI6IjJlMjQzODI5Y2EyNzdlZGM3MzNjYTFiNTZkMjk1OGZiMjAzNTlmM2M2YjRmNDI1NTljZDJjNmJjMDhiNDJmODMiLCJ0aW1lb3V0X3NlY29uZHMiOjEyMCwid3JpdGVfcm9vdHMiOlsiL3RtcCIsIi93b3JrIl19LCJzY2hlbWFfdmVyc2lvbiI6MX0='

if [ "$(id -un)" = "kensei" ]; then echo "Run this as sahil, not kensei."; exit 1; fi
if [ "$(date +%s)" -ge "$EXPIRES" ]; then echo "This request has expired. Ask KENSEI for a fresh one."; exit 1; fi

work="$(mktemp -d "$HOME/.modernisation-sign.XXXXXX")"
trap 'rm -rf "$work"' EXIT
printf '%s' "$CANDIDATE_B64" | base64 -d > "$work/candidate.json"
cat > "$work/owner-public.pem" <<'PEM'
-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAKpMZpRxBfeT0ZqKa87hpT1kXdZCHnYK6hHqh0f6Fb+8=
-----END PUBLIC KEY-----
PEM
echo "$CANDIDATE_SHA  $work/candidate.json" | sha256sum -c --quiet

cat <<'TXT'

You are approving exactly ONE one-off test run:
  The UPGRADED walkie-talkie copy, with two test tools updated
  (pytest-asyncio 1.4.0, starlette 0.52.1), running the same 20 tests.
No network, read-only code, non-root, 512 MB memory, 2-minute cap,
throwaway container. No installs, no pushes, nothing live touched.
The signature works once, only for this exact run, until Mon 19 Oct 21:25 BST.

TXT

default=""
for f in "$HOME"/modernisation-owner.*/owner.key "$HOME"/owner.key; do
  if [ -f "$f" ]; then default="$f"; break; fi
done
if [ -n "$default" ]; then
  read -r -p "Path to your owner.key [$default]: " key; key="${key:-$default}"
else
  read -r -p "Path to your owner.key: " key
fi
key="${key/#\~/$HOME}"
[ -f "$key" ] || { echo "No file at: $key"; exit 1; }

if ! openssl pkey -in "$key" -pubout 2>/dev/null | cmp -s - "$work/owner-public.pem"; then
  echo "That key is not the enrolled owner key. Nothing was signed."; exit 1
fi

read -r -p "Type YES to sign this run: " ok
[ "$ok" = "YES" ] || { echo "Cancelled. Nothing was signed."; exit 1; }

openssl pkeyutl -sign -rawin -inkey "$key" -in "$work/candidate.json" -out "$work/candidate.sig"
openssl pkeyutl -verify -rawin -pubin -inkey "$work/owner-public.pem" \
    -in "$work/candidate.json" -sigfile "$work/candidate.sig" >/dev/null \
    || { echo "Signature check failed. Nothing saved."; exit 1; }

umask 022
printf 'candidate: %s\n' "$(base64 -w0 "$work/candidate.sig")" > "$OUT"
chmod 644 "$OUT"

echo
echo "Done. Signature verified and saved to $OUT"
echo "Tell KENSEI: signed."
