---
name: youtube-summary
version: "1.1.0"
author: giskard
description: "Summarize any YouTube video by dropping the link in chat. Supports custom prompts — paste the URL followed by your instructions (e.g. 'focus on the technical details'). Triggers on YouTube URLs."
tags: [youtube, video, summary, transcript]
license: MIT
---

# YouTube Summary Skill

Summarize YouTube videos by extracting transcripts and generating structured summaries.

## Setup

1. Sign up at [transcriptapi.com](https://transcriptapi.com) ($5/mo for 1,000 transcripts)
2. Store the API key in `pass`:
   ```bash
   pass init --path transcriptapi 01A60665BAD5A8CC 48C81D44519B6336
   pass insert transcriptapi/api-key
   ```
3. Install Python dependencies: `pip install -r skills/youtube-summary/requirements.txt`

## Detection

Trigger on messages containing YouTube URLs matching any of:
- `youtube.com/watch?v=ID`
- `youtu.be/ID`
- `youtube.com/shorts/ID`
- `m.youtube.com/watch?v=ID`
- `youtube.com/live/ID`

## ⚠️ Critical Rules

- **NEVER use web_search as a fallback.** If transcript extraction fails, report the error and stop.
- **NEVER fabricate transcript content.** Only summarize what the extraction script returns.
- **Always run the extraction script.** Do not skip it, even for well-known videos.

## Workflow

### Step 1: Extract transcript

```bash
_yt_key_file=$(mktemp) && pass transcriptapi/api-key > "$_yt_key_file" && python3 skills/youtube-summary/scripts/extract.py "YOUTUBE_URL_OR_ID" --api-key-file "$_yt_key_file"; rm -f "$_yt_key_file"
```

Parse stdout:
- `PROGRESS:` lines → relay to user as status updates (optional)
- `ERROR:` lines → relay error to user, stop
- `RESULT:` line → parse the JSON after `RESULT: ` — it contains: `header`, `transcript`, `language`, `tokens`, `title`, `channel`, `duration_str`

### Step 2: Summarize the transcript

Use the extracted transcript to generate a summary. The summary language must match the transcript language (from the `language` field).

**If tokens < 50000** — single-pass: summarize the full transcript in one request.

**If tokens ≥ 50000** — tell the user it's a long video and summarize the first ~40K tokens with a note that it was truncated.

**Default summary format** (use when no custom prompt given):

```
{header}

**TL;DR:** 2-3 sentence summary.

**Key Points:**
• Point one
• Point two
• (3-7 total)

**Notable Quotes:** (only if genuinely quotable lines exist)
> "Quote here"
```

**Custom prompt** — if the user included text alongside the URL, append it as additional instructions for the summary.

### Step 3: Reply

- Keep output under 4000 characters for Telegram
- If the summary would exceed 4000 chars, send the TL;DR first, then the rest as a follow-up
- Always include the header line from the extraction result

## Error Handling

- `ERROR: API_ERROR: Invalid API key` → "TranscriptAPI key is invalid. Check `pass transcriptapi/api-key`."
- `ERROR: No transcript available` → "This video doesn't have captions available."
- `ERROR: Video not found` → "Couldn't find that video — double-check the URL."
- Any other `ERROR:` → relay the message as-is. **Do NOT fall back to web_search.**

## Why TranscriptAPI?

YouTube aggressively blocks datacenter/IPv6 ranges from accessing transcripts. Most cloud VPS (Hetzner, DigitalOcean, AWS, etc.) are blocked — the `youtube-transcript-api` library fails with "Could not find a transcript" for a huge portion of videos.

TranscriptAPI.com runs the requests from residential IPs, bypassing these blocks. The $5/mo gets you 1,000 reliable transcript fetches.
- 💡 Tip: Add instructions after the URL to customize the summary (e.g. "focus on the technical details")
