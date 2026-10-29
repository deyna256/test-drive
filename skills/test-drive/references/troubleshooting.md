# Troubleshooting

## Browser CLI setup

- `test-drive setup-agent-browser` needs network access to GitHub. A digest mismatch or failed download leaves nothing behind; report the message rather than retrying indefinitely.
- An incompatible `agent-browser` already in the runtime directory is never overwritten: ask the user to remove it or choose another directory with `--directory` and `TEST_DRIVE_RUNTIME_DIR`.
- A system without a published binary needs agent-browser installed another way (see agent-browser's installation guide) and `TEST_DRIVE_AGENT_BROWSER` set to it.

## Startup and daemon failures

- Inspect the error first. For unclear daemon failures, use `--debug` and read the isolated session's log before choosing a remedy.
- For an unwritable or overly long socket path, set `AGENT_BROWSER_SOCKET_DIR` to a short, writable, task-specific directory, use a short session name, and keep that setting for every browser command.
- If the environment denies socket binding or connection (`EPERM`/`EACCES`) or blocks required network access, request the minimum permissions needed for the failing command, local socket, and destination through the host's approval mechanism, if required and available. Retry after a targeted correction or approval.
- If access cannot be granted, explain the cause and mark affected criteria blocked. Do not assume every timeout or DNS error needs elevated permissions, retry indefinitely, or bypass a denial through `sudo` or indirect commands.

## Memory

If available memory is critically low, stop rather than repeatedly launching browsers; preserve partial evidence and explain the blockage. Use an appropriate host resource limit or a lower recording frame rate when necessary.

## Recording

- WebM recording requires `ffmpeg` on `PATH` with the `libvpx` VP8 encoder: for example `sudo apt install ffmpeg`, `brew install ffmpeg`, or `winget install Gyan.FFmpeg`.
- If `record stop` fails, retain any partial file separately, omit `video`, and identify the file and the failure in `video_reason`. A truncated recording can still decode and must not be presented as complete.
