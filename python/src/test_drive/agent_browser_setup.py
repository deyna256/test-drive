"""Set up the browser CLI without changing a global installation."""

import argparse
import hashlib
import http.client
import os
import platform
import sys
import tempfile
import urllib.request
from pathlib import Path

from . import agent_browser

# The tested release. Update the version and every digest together, from
# `gh release view v<version> --repo vercel-labs/agent-browser --json assets`.
VERSION = "0.40.0"
RELEASE = f"https://github.com/vercel-labs/agent-browser/releases/download/v{VERSION}/"
DIGESTS = {
    "darwin-arm64": "b064c9107a0431c76d8916e47c2c8ac322f49c2b2720d6c9036ab538ec1ed911",
    "darwin-x64": "478cba056938c5cde286fbeea3994a8b8144f2e18f054684b93abb80c0340d25",
    "linux-arm64": "f33b4dd9bd7707ad952125937f9de18f93548c5d51283b18092fe21ced6b9e53",
    "linux-musl-arm64": "3d4352c0b39f173896aa12af0e63d5905ac8ce7c95575fe6f1f93ce21f9b9e26",
    "linux-musl-x64": "aeebf976eb429064efb10179ccdf737ec7d798c019bae7067ce2751c9c6e176a",
    "linux-x64": "da26cc8029c004325b960fa955951063380cb61e622cc580fd5adf3aa89e4676",
    "win32-x64.exe": "b142ca8946efda2d506e0947b232596e7949f08296e6b953b57f63eb50fee751",
}


def platform_name() -> str | None:
    """Name the release binary for this system, as agent-browser's own launcher does."""
    machine = {"x86_64": "x64", "amd64": "x64", "aarch64": "arm64", "arm64": "arm64"}.get(
        platform.machine().lower()
    )
    if sys.platform == "darwin":
        system = "darwin"
    elif sys.platform.startswith("linux"):
        system = "linux" if platform.libc_ver()[0] == "glibc" else "linux-musl"
    elif sys.platform == "win32":
        return "win32-x64.exe" if machine == "x64" else None
    else:
        return None
    return f"{system}-{machine}" if machine else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Set up Test Drive's browser CLI")
    parser.add_argument("--directory", type=Path, default=agent_browser.runtime_directory())
    args = parser.parse_args()
    found, error = agent_browser.find()
    if found:
        print(f"Using agent-browser: {found}")
        return 0
    if os.environ.get("TEST_DRIVE_AGENT_BROWSER"):
        print(error, file=sys.stderr)
        return 1

    target = args.directory.expanduser().resolve()
    binary = agent_browser.runtime_browsers(target)[0]
    if binary.exists():
        found, error = agent_browser.check(binary)
        if found:
            print(f"Using agent-browser: {found}")
            return 0
        print(
            f"{error} It was not changed; remove it or choose another directory.", file=sys.stderr
        )
        return 1
    name = platform_name()
    if name not in DIGESTS:
        print(
            f"No agent-browser {VERSION} binary is published for {sys.platform} {platform.machine()}."
            " Install agent-browser another way and set TEST_DRIVE_AGENT_BROWSER.",
            file=sys.stderr,
        )
        return 1

    temporary = None
    try:
        target.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            dir=target, prefix=".agent-browser-", delete=False
        ) as file:
            temporary = Path(file.name)
            digest = hashlib.sha256()
            with urllib.request.urlopen(RELEASE + f"agent-browser-{name}", timeout=60) as response:
                while chunk := response.read(1 << 20):
                    digest.update(chunk)
                    file.write(chunk)
        if digest.hexdigest() != DIGESTS[name]:
            print(
                "The downloaded agent-browser does not match its SHA-256 digest.", file=sys.stderr
            )
            return 1
        temporary.chmod(0o755)
        temporary.replace(binary)
        temporary = None
        found, error = agent_browser.check(binary)
        if not found:
            binary.unlink()
            print(f"The installed agent-browser could not be verified: {error}", file=sys.stderr)
            return 1
    except (OSError, http.client.HTTPException) as exc:
        print(f"Could not download agent-browser {VERSION}: {exc}", file=sys.stderr)
        return 1
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print(f"Installed agent-browser: {found}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
