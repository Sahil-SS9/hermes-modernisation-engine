#!/usr/bin/env bash
# Sign the two Modernisation Engine v3 trial requests. Run as YOURSELF (sahil).
# Your private key never leaves your account and is never printed or copied.
# The signatures (not secret, one-use, bound to these exact two test runs) are
# saved to ~/modernisation-v3-signatures.txt so KENSEI can pick them up.
set -euo pipefail

EXPIRES=1792440398
BASELINE_SHA=c7a13e63dfe89816f3d31efa8490eb383606dc1ccfa604392a6bed718219400f
CANDIDATE_SHA=d990670fa3806a9144695a5b6d8ab759a0e0d8db53f5795686fac0ee9272fea8
OUT="$HOME/modernisation-v3-signatures.txt"
BASELINE_B64='eyJleHBpcmVzX2F0IjoxNzkyNDQwMzk4LCJtYXhfdXNlcyI6MSwibm9uY2UiOiIxYWRkY2Y2NWMyNDM0YTBmYWMyMjRmN2U4NDQxZDVjMSIsIm9wZXJhdGlvbiI6eyJhY3RvciI6InNhaGlsIiwiYXJndiI6WyJweXRob24iLCItQiIsIi1jIiwiaW1wb3J0IGJhc2U2NCxoYXNobGliLGpzb24sc3lzLHhtbC5ldHJlZS5FbGVtZW50VHJlZSBhcyBFXG5pbXBvcnQgcHl0ZXN0XG5zdGF0dXM9aW50KHB5dGVzdC5tYWluKFsndGVzdHMvdW5pdC90ZXN0X2Rhc2hib2FyZF9hcGkucHknLCd0ZXN0cy9zZWN1cml0eS90ZXN0X3dzX2F1dGhfZmFpbHNfY2xvc2VkLnB5JywnLXAnLCdubzpjYWNoZXByb3ZpZGVyJywnLW8nLCdhZGRvcHRzPScsJy0tanVuaXR4bWw9L3RtcC93YWxraWUtcmVzdWx0LnhtbCcsJy1yYSddKSlcbnN5cy5zdGRvdXQuZmx1c2goKVxudHJ5OlxuICAgIHdpdGggb3BlbignL3RtcC93YWxraWUtcmVzdWx0LnhtbCcsJ3JiJykgYXMgc3RyZWFtOnJhdz1zdHJlYW0ucmVhZCgxMDQ4NTc3KVxuZXhjZXB0IE9TRXJyb3I6XG4gICAgcmF3PWInJ1xuY291bnRzPU5vbmVcbmlmIHJhdyBhbmQgbGVuKHJhdyk8PTEwNDg1NzY6XG4gICAgdHJ5OlxuICAgICAgICBub2Rlcz1saXN0KEUuZnJvbXN0cmluZyhyYXcpLml0ZXIoJ3Rlc3RjYXNlJykpXG4gICAgICAgIGNvdW50cz17J2NvbGxlY3RlZCc6bGVuKG5vZGVzKSwnZmFpbHVyZXMnOnN1bShuLmZpbmQoJ2ZhaWx1cmUnKSBpcyBub3QgTm9uZSBmb3IgbiBpbiBub2RlcyksJ2Vycm9ycyc6c3VtKG4uZmluZCgnZXJyb3InKSBpcyBub3QgTm9uZSBmb3IgbiBpbiBub2RlcyksJ3NraXBwZWQnOnN1bShuLmZpbmQoJ3NraXBwZWQnKSBpcyBub3QgTm9uZSBmb3IgbiBpbiBub2Rlcyl9XG4gICAgZXhjZXB0IEUuUGFyc2VFcnJvcjpcbiAgICAgICAgY291bnRzPU5vbmVcbnJhdz1yYXdbOjEwNDg1NzZdXG5wcmludCgnUlVOTkVSX1BZVEVTVF9TVEFUVVM9JytzdHIoc3RhdHVzKSlcbnByaW50KCdSVU5ORVJfQ09VTlRTX0pTT049Jytqc29uLmR1bXBzKGNvdW50cyxzb3J0X2tleXM9VHJ1ZSkpXG5wcmludCgnUlVOTkVSX0VOVl9KU09OPScranNvbi5kdW1wcyh7J3B5dGhvbic6c3lzLnZlcnNpb259KSlcbnByaW50KCdSVU5ORVJfSlVOSVRfQllURVM9JytzdHIobGVuKHJhdykpKVxucHJpbnQoJ1JVTk5FUl9KVU5JVF9TSEEyNTY9JytoYXNobGliLnNoYTI1NihyYXcpLmhleGRpZ2VzdCgpKVxucHJpbnQoJ1JVTk5FUl9KVU5JVF9CRUdJTicpXG5wcmludChiYXNlNjQuYjY0ZW5jb2RlKHJhdykuZGVjb2RlKCkpXG5wcmludCgnUlVOTkVSX0pVTklUX0VORCcsZmx1c2g9VHJ1ZSlcbnJhaXNlIFN5c3RlbUV4aXQoMCBpZiBzdGF0dXM9PTAgYW5kIGNvdW50cz09eydjb2xsZWN0ZWQnOjIwLCdmYWlsdXJlcyc6MCwnZXJyb3JzJzowLCdza2lwcGVkJzowfSBlbHNlIDIpXG4iXSwiYXR0ZW1wdF9pZCI6ImJhc2VsaW5lLWJlN2U1NTIxYzc4MjQ0ZmI4NjMxMDQ2NGVhYmU4ZmZkIiwiY2FuZGlkYXRlX2RpZ2VzdCI6IjkzZjQyMTkzYmQwYjc1MjliMWJkNGRiMGYyMzY5ZDBlYzRkZDg3MmE2NWMzODI0NDk4MWMwNjExNmIzM2FiMDMiLCJlbnZpcm9ubWVudF9kaWdlc3QiOiJmMGJmMWZlYTMzNDRjZWJiZDRjMDg5YTBjNzVjNzJmNTQ5NGZhZmRkY2ExNzZhYjZjNjFjYmZlMmE3Y2YzYzFkIiwiaW1hZ2VfZGlnZXN0IjoiNDk4MDhjYjBiOTkwOTUwNWU5MDZmY2VmNWUwZWEzNzM1NjZjOTZhMDUwOGNiYzNmNjBjMmZjMzhkZTA4MjE3ZiIsImpvYl9pZCI6IndhbGtpZS1weXRob24zMTQtZmFzdGFwaS12MyIsIm5ldHdvcmsiOiJub25lIiwib3JhY2xlX2RpZ2VzdCI6ImNmYzlkOTRlZjM4ZGUxYjdhODA1M2ZjYTM0NmZmODYxZTZkODIzYzkwODg3N2ZiNDViZTI4MjkwODQ4OTEyNzUiLCJvdXRwdXRfbGltaXRfYnl0ZXMiOjQxOTQzMDQsInByb2ZpbGUiOiJkZWZhdWx0IiwicmVhZF9yb290cyI6WyIvc291cmNlIl0sInNjaGVtYV92ZXJzaW9uIjoxLCJzb3VyY2VfZGlnZXN0IjoiOTNmNDIxOTNiZDBiNzUyOWIxYmQ0ZGIwZjIzNjlkMGVjNGRkODcyYTY1YzM4MjQ0OTgxYzA2MTE2YjMzYWIwMyIsInRpbWVvdXRfc2Vjb25kcyI6MTIwLCJ3cml0ZV9yb290cyI6WyIvdG1wIiwiL3dvcmsiXX0sInNjaGVtYV92ZXJzaW9uIjoxfQ=='
CANDIDATE_B64='eyJleHBpcmVzX2F0IjoxNzkyNDQwMzk4LCJtYXhfdXNlcyI6MSwibm9uY2UiOiJlZjAyNjg3MWI2MjU0ZTNmODA1YmZjZjhiMGE3Y2EzNyIsIm9wZXJhdGlvbiI6eyJhY3RvciI6InNhaGlsIiwiYXJndiI6WyIvY2FuZGlkYXRlLy52ZW52L2Jpbi9weXRob24iLCItQiIsIi1jIiwiaW1wb3J0IGJhc2U2NCxoYXNobGliLGpzb24sc3lzLHhtbC5ldHJlZS5FbGVtZW50VHJlZSBhcyBFXG5pbXBvcnQgcHl0ZXN0XG5zdGF0dXM9aW50KHB5dGVzdC5tYWluKFsndGVzdHMvdW5pdC90ZXN0X2Rhc2hib2FyZF9hcGkucHknLCd0ZXN0cy9zZWN1cml0eS90ZXN0X3dzX2F1dGhfZmFpbHNfY2xvc2VkLnB5JywnLXAnLCdubzpjYWNoZXByb3ZpZGVyJywnLW8nLCdhZGRvcHRzPScsJy0tanVuaXR4bWw9L3RtcC93YWxraWUtcmVzdWx0LnhtbCcsJy1yYSddKSlcbnN5cy5zdGRvdXQuZmx1c2goKVxudHJ5OlxuICAgIHdpdGggb3BlbignL3RtcC93YWxraWUtcmVzdWx0LnhtbCcsJ3JiJykgYXMgc3RyZWFtOnJhdz1zdHJlYW0ucmVhZCgxMDQ4NTc3KVxuZXhjZXB0IE9TRXJyb3I6XG4gICAgcmF3PWInJ1xuY291bnRzPU5vbmVcbmlmIHJhdyBhbmQgbGVuKHJhdyk8PTEwNDg1NzY6XG4gICAgdHJ5OlxuICAgICAgICBub2Rlcz1saXN0KEUuZnJvbXN0cmluZyhyYXcpLml0ZXIoJ3Rlc3RjYXNlJykpXG4gICAgICAgIGNvdW50cz17J2NvbGxlY3RlZCc6bGVuKG5vZGVzKSwnZmFpbHVyZXMnOnN1bShuLmZpbmQoJ2ZhaWx1cmUnKSBpcyBub3QgTm9uZSBmb3IgbiBpbiBub2RlcyksJ2Vycm9ycyc6c3VtKG4uZmluZCgnZXJyb3InKSBpcyBub3QgTm9uZSBmb3IgbiBpbiBub2RlcyksJ3NraXBwZWQnOnN1bShuLmZpbmQoJ3NraXBwZWQnKSBpcyBub3QgTm9uZSBmb3IgbiBpbiBub2Rlcyl9XG4gICAgZXhjZXB0IEUuUGFyc2VFcnJvcjpcbiAgICAgICAgY291bnRzPU5vbmVcbnJhdz1yYXdbOjEwNDg1NzZdXG5wcmludCgnUlVOTkVSX1BZVEVTVF9TVEFUVVM9JytzdHIoc3RhdHVzKSlcbnByaW50KCdSVU5ORVJfQ09VTlRTX0pTT049Jytqc29uLmR1bXBzKGNvdW50cyxzb3J0X2tleXM9VHJ1ZSkpXG5wcmludCgnUlVOTkVSX0VOVl9KU09OPScranNvbi5kdW1wcyh7J3B5dGhvbic6c3lzLnZlcnNpb259KSlcbnByaW50KCdSVU5ORVJfSlVOSVRfQllURVM9JytzdHIobGVuKHJhdykpKVxucHJpbnQoJ1JVTk5FUl9KVU5JVF9TSEEyNTY9JytoYXNobGliLnNoYTI1NihyYXcpLmhleGRpZ2VzdCgpKVxucHJpbnQoJ1JVTk5FUl9KVU5JVF9CRUdJTicpXG5wcmludChiYXNlNjQuYjY0ZW5jb2RlKHJhdykuZGVjb2RlKCkpXG5wcmludCgnUlVOTkVSX0pVTklUX0VORCcsZmx1c2g9VHJ1ZSlcbnJhaXNlIFN5c3RlbUV4aXQoMCBpZiBzdGF0dXM9PTAgYW5kIGNvdW50cz09eydjb2xsZWN0ZWQnOjIwLCdmYWlsdXJlcyc6MCwnZXJyb3JzJzowLCdza2lwcGVkJzowfSBlbHNlIDIpXG4iXSwiYXR0ZW1wdF9pZCI6ImNhbmRpZGF0ZS0zNzcyMzUyNzQyZDc0YjY4YTE2MTEyY2YzZjBhNDM0NSIsImNhbmRpZGF0ZV9kaWdlc3QiOiIxMDA2MWJmYjZhOTY0ZDk2ZDllMjNkMmVmZGIyNjc1M2RiNTMxZTJkMTc0Y2UzM2U3MTRlMjQ4NjQxZGFmZGNmIiwiZW52aXJvbm1lbnRfZGlnZXN0IjoiYjY4NWQzYWVhMTJlYjhmYzM1ZGIwODgwNzg0ZjQwZjFkNGU1OWIzODJjMDMyZmRlMjU0MDlmZGNlYzYwODQ0YSIsImltYWdlX2RpZ2VzdCI6ImM5MzRhMjZmYjMzYzVkYzc0YWE2YzQzZmY5MzAyMjYwNGRkOGFkZDc1M2ZlNGZmZDdmYmIzMWUxNjJhNGU5OTkiLCJqb2JfaWQiOiJ3YWxraWUtcHl0aG9uMzE0LWZhc3RhcGktdjMiLCJuZXR3b3JrIjoibm9uZSIsIm9yYWNsZV9kaWdlc3QiOiJjZmM5ZDk0ZWYzOGRlMWI3YTgwNTNmY2EzNDZmZjg2MWU2ZDgyM2M5MDg4NzdmYjQ1YmUyODI5MDg0ODkxMjc1Iiwib3V0cHV0X2xpbWl0X2J5dGVzIjo0MTk0MzA0LCJwcm9maWxlIjoiZGVmYXVsdCIsInJlYWRfcm9vdHMiOlsiL3NvdXJjZSJdLCJzY2hlbWFfdmVyc2lvbiI6MSwic291cmNlX2RpZ2VzdCI6IjEwMDYxYmZiNmE5NjRkOTZkOWUyM2QyZWZkYjI2NzUzZGI1MzFlMmQxNzRjZTMzZTcxNGUyNDg2NDFkYWZkY2YiLCJ0aW1lb3V0X3NlY29uZHMiOjEyMCwid3JpdGVfcm9vdHMiOlsiL3RtcCIsIi93b3JrIl19LCJzY2hlbWFfdmVyc2lvbiI6MX0='

if [ "$(id -un)" = "kensei" ]; then echo "Run this as sahil, not kensei."; exit 1; fi
if [ "$(date +%s)" -ge "$EXPIRES" ]; then echo "These requests have expired. Ask KENSEI for fresh ones."; exit 1; fi

work="$(mktemp -d "$HOME/.modernisation-sign.XXXXXX")"
trap 'rm -rf "$work"' EXIT
printf '%s' "$BASELINE_B64" | base64 -d > "$work/baseline.json"
printf '%s' "$CANDIDATE_B64" | base64 -d > "$work/candidate.json"
cat > "$work/owner-public.pem" <<'PEM'
-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAKpMZpRxBfeT0ZqKa87hpT1kXdZCHnYK6hHqh0f6Fb+8=
-----END PUBLIC KEY-----
PEM
echo "$BASELINE_SHA  $work/baseline.json"  | sha256sum -c --quiet
echo "$CANDIDATE_SHA  $work/candidate.json" | sha256sum -c --quiet

cat <<'TXT'

You are approving exactly two one-off test runs:
  1. The ORIGINAL walkie-talkie code: its 20 existing API/login tests.
  2. The UPGRADED copy (Python 3.14 + newer FastAPI): the same 20 tests.
Each run: no network, read-only code, non-root, 512 MB memory, 2-minute cap,
throwaway container. No installs, no pushes, nothing live touched.
Each signature works once, only for these exact runs, until Mon 19 Oct 21:06 BST.

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

# Make sure this is the enrolled owner key before signing anything.
if ! openssl pkey -in "$key" -pubout 2>/dev/null | cmp -s - "$work/owner-public.pem"; then
  echo "That key is not the enrolled owner key. Nothing was signed."; exit 1
fi

read -r -p "Type YES to sign both runs: " ok
[ "$ok" = "YES" ] || { echo "Cancelled. Nothing was signed."; exit 1; }

for phase in baseline candidate; do
  openssl pkeyutl -sign -rawin -inkey "$key" -in "$work/$phase.json" -out "$work/$phase.sig"
  openssl pkeyutl -verify -rawin -pubin -inkey "$work/owner-public.pem" \
      -in "$work/$phase.json" -sigfile "$work/$phase.sig" >/dev/null \
      || { echo "Signature check failed for $phase. Nothing saved."; exit 1; }
done

umask 022
{
  printf 'baseline: %s\n'  "$(base64 -w0 "$work/baseline.sig")"
  printf 'candidate: %s\n' "$(base64 -w0 "$work/candidate.sig")"
} > "$OUT"
chmod 644 "$OUT"

echo
echo "Done. Both signatures verified and saved to $OUT"
echo "Tell KENSEI: signed."
