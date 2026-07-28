# Security Policy

WorldBench has not undergone an independent security audit. Please do not treat it as a sandbox for untrusted code, untrusted plugins, or arbitrary model downloads.

## Supported Versions

Security fixes are expected to target the latest public release and the `main` branch.

## Reporting A Vulnerability

Please report suspected vulnerabilities privately. Do not open a public issue containing exploit details, credentials, private data links, or sensitive logs.

Email: `writetoayushadi@gmail.com`

Please include:

- affected WorldBench version or commit
- operating system and Python version
- reproduction steps
- whether the issue involves untrusted JSON, paths, video files, subprocesses, or generated artifacts
- any suggested mitigation

## Current Security Boundaries

- Plugins must be imported and registered explicitly by the caller.
- WorldBench does not dynamically install third-party plugins or execute remote code.
- Result verification reads bounded JSON and checks hashes when local paths are available.
- Video decoding still depends on local decoder libraries and should not be treated as safe for hostile media files.
