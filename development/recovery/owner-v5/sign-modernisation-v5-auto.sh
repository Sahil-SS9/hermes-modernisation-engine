#!/usr/bin/env bash
# Owner-only convenience launcher. Locate an EXISTING registered key privately,
# then hand the owner's literal YES and its path to the UNCHANGED audited signer.
# Never generate, enrol, rotate, print or copy a private key; never run a trial.
set -euo pipefail

OWNER_USER="sahil"
SIGNER="/home/kensei/projects/modernisation-benchmarks/control/trial-v5/sign-owner-trial-v5.sh"
SIGNER_SHA="e5145e9199be39fb7881e94e93b9201063e25b00347aa1259203e789b7c98f9e"
EXPIRES_EPOCH=1792976951
ENROLLED_PEM='-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAKpMZpRxBfeT0ZqKa87hpT1kXdZCHnYK6hHqh0f6Fb+8=
-----END PUBLIC KEY-----'

refuse() { printf '%s\n' "$*" >&2; exit 1; }
[ "$(id -un)" = "$OWNER_USER" ] && [ "$(id -u)" -ne 0 ] || refuse "Run this from your normal sahil terminal, not kensei or sudo."
[ "$(date +%s)" -lt "$EXPIRES_EPOCH" ] || refuse "The approval window expired. Nothing was signed."
[ -f "$SIGNER" ] && [ ! -L "$SIGNER" ] || refuse "The reviewed signer is unavailable. Nothing was signed."
[ "$(sha256sum "$SIGNER" | cut -d' ' -f1)" = "$SIGNER_SHA" ] || refuse "The reviewed signer changed. Nothing was signed."

work=$(mktemp -d "$HOME/.modernisation-v5-help.XXXXXX")
cleanup() {
  local name
  for name in enrolled.pem enrolled.der key.der signing.log; do
    rm -f -- "$work/$name"
  done
  if ! rmdir -- "$work"; then
    printf 'Temporary PUBLIC verification files retained at %s\n' "$work" >&2
  fi
}
trap cleanup EXIT
printf '%s\n' "$ENROLLED_PEM" > "$work/enrolled.pem"
openssl pkey -pubin -in "$work/enrolled.pem" -outform DER > "$work/enrolled.der"

# These are precisely the locations used by the earlier owner setup/sign script.
# Only the owner process looks there. Compare PUBLIC halves, never key contents.
shopt -s nullglob
key=""
for candidate in "$HOME"/modernisation-owner.*/owner.key "$HOME"/owner.key; do
  [ -f "$candidate" ] && [ ! -L "$candidate" ] || continue
  [ ! -L "$(dirname "$candidate")" ] || continue
  [ "$(stat -c '%u' "$candidate")" = "$(id -u)" ] || continue
  # Empty passin prevents unexpected passphrase prompts while discovering files.
  # An encrypted/unreadable or different key is NOT replaced or re-enrolled.
  if openssl pkey -in "$candidate" -passin pass: -pubout -outform DER > "$work/key.der" 2>/dev/null \
      && cmp -s "$work/key.der" "$work/enrolled.der"; then
    key=$candidate
    break
  fi
done
[ -n "$key" ] || refuse "I could not locate the registered key in the earlier setup folders. Nothing was signed or changed. Tell KENSEI: key not found."

printf '%s\n' \
  'Found your registered approval key automatically.' \
  'You do not need to know or type its filename.' \
  '' \
  'Approve two isolated test runs: the original and upgraded project COPIES.' \
  'Each runs 20 selected checks, with no network and a two-minute limit.' \
  'Your original project stays unchanged. No installation or deployment.' \
  'This signs permission only; it does not start the tests.' \
  'Your private key stays in your account and is never printed or copied.'
read -r -p 'Type YES to approve these two test runs: ' answer
[ "$answer" = 'YES' ] || refuse 'Cancelled. Nothing was signed.'

# The consent is the literal answer typed above, not an automatic YES. The pinned
# signer still performs every original pin/key/signature/output check itself.
# Its duplicate summary is kept in a temporary PUBLIC log, not shown twice.
if printf '%s\n%s\n' "$answer" "$key" | TMPDIR="$work" bash "$SIGNER" > "$work/signing.log" 2>&1; then
  printf 'Approved. Tell KENSEI: done.\n'
else
  result=$?
  cat -- "$work/signing.log"
  exit "$result"
fi
