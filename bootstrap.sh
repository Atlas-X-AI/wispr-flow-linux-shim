#!/usr/bin/env bash
# Pinned GitHub-release bootstrap for Atlas Wispr.
set -euo pipefail

version="${ATLAS_WISPR_VERSION:-v1.1.3}"
plain_version="${version#v}"
release_base="${ATLAS_WISPR_RELEASE_BASE:-https://github.com/Atlas-X-AI/wispr-flow-linux-shim/releases/download/${version}}"
archive="atlas-wispr-${plain_version}.tar.gz"
checksum="${archive}.sha256"
tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/atlas-wispr-bootstrap.XXXXXX")"
trap 'rm -rf -- "$tmpdir"' EXIT

for command in curl tar sha256sum; do
    command -v "$command" >/dev/null 2>&1 || {
        printf 'FAIL: %s is required by the bootstrap.\n' "$command" >&2
        exit 1
    }
done

printf 'Atlas Wispr %s: downloading the pinned GitHub release...\n' "$version"
curl -fsSL --retry 3 "${release_base}/${archive}" -o "${tmpdir}/${archive}"
curl -fsSL --retry 3 "${release_base}/${checksum}" -o "${tmpdir}/${checksum}"
(
    cd "$tmpdir"
    sha256sum --check --strict "$checksum"
)
printf 'PASS: release checksum verified\n'

tar -xzf "${tmpdir}/${archive}" -C "$tmpdir"
package_dir="${tmpdir}/atlas-wispr-${plain_version}"
[ -x "${package_dir}/install.sh" ] || {
    printf 'FAIL: the verified release does not contain install.sh.\n' >&2
    exit 1
}

revision="${version}"
if [ -f "${package_dir}/REVISION" ]; then
    revision="$(tr -d '[:space:]' < "${package_dir}/REVISION")"
fi
ATLAS_WISPR_RELEASE_REVISION="$revision" "${package_dir}/install.sh" --provision
