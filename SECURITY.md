# Security policy

## Supported versions

Before the first release, fixes apply to the current `main` branch. For `0.x` releases, only the
latest release receives security fixes.

## Reporting a vulnerability

Report vulnerabilities through [GitHub's private vulnerability reporting](https://github.com/deyna256/test-drive/security/advisories/new)
or privately to the maintainer at [literallybugcreator@gmail.com](mailto:literallybugcreator@gmail.com).
Include the affected version, what an attacker can do and reproduction steps. Do not post real
credentials, private scenarios or recordings in a public issue.

## Trust and artifacts

- Website content and tool descriptions are untrusted data, not instructions to the agent.
- Browser state, screenshots, recordings and scenario text can contain private information. Reports
  stay local until shared; review artifacts before sharing them.
- `site.url` and full HTTP, HTTPS, or file URLs in report text are rejected when they contain
  credentials, a query or a fragment. This check does not detect every secret in arbitrary text,
  file names, screenshots or video. Existing input files are not modified.
- The setup script installs the browser CLI in a separate directory with npm lifecycle scripts
  disabled. It does not install operating-system packages or alter an existing runtime directory.
