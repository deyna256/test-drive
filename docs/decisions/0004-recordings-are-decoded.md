# 4. Recordings are verified by decoding them with ffmpeg

**Status:** Accepted

## Context

A report must not present a recording that cannot be played, and must not read files outside the
report folder or the network while checking it: a playlist can reference other files. A file's
extension or header does not show whether its frames decode.

## Decision

`render-report` decodes the first video stream of each recording with ffmpeg, reading only the opened
file through the `fd` protocol (`pipe` where `fd` is unavailable), with `-xerror` and a 30 s timeout.
A recording is embedded only if ffmpeg exits successfully and reports at least one frame. Otherwise
the report says it is unavailable, could not be decoded or could not be verified.

## Alternatives

- **Check only that the file exists and is not empty**: a truncated or corrupt file would appear as a
  working video.
- **Decode only the first frame**: much faster, but corruption later in the file would go unnoticed.
- **Cache results by path, size and modification time**: avoids decoding again on every render, but
  adds a state file to the report folder.

## Consequences

- ffmpeg is required to embed recordings; it is already required to record them.
- Every render decodes every recording again, and a recording that takes longer than 30 s to decode
  is shown as unverified. Typical scenario recordings decode in well under a second, so this is kept
  until long recordings make it a problem.
- Decoding does not prove that a recording is complete or shows what the report claims.
