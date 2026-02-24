# YouTube Summary Skill — Security & UX Review

**Date:** 2026-02-23
**Reviewer:** Giskard (subagent)

---

## 1. Security Findings

### 🔴 HIGH — API Key Exposed in Process List

**Location:** SKILL.md workflow, Step 1

```bash
python3 scripts/extract.py "URL" --api-key "$(pass transcriptapi/api-key)"
```

The API key is passed as a CLI argument. Any user on the system can see it via `ps aux`. The key appears in `/proc/<pid>/cmdline` for the entire duration of the process.

**Recommendation:** Remove `--api-key` CLI arg. Pass via environment variable only:
```bash
TRANSCRIPT_API_KEY="$(pass transcriptapi/api-key)" python3 scripts/extract.py "URL"
```
Environment variables are NOT visible in `ps` output.

---

### 🟡 MEDIUM — Subprocess Call in `get_metadata()` with Unsanitized Input

**Location:** `extract.py:get_metadata()`, line ~45

```python
subprocess.run(["yt-dlp", "--dump-json", "--no-download", f"https://www.youtube.com/watch?v={video_id}"], ...)
```

The `video_id` is validated by `extract_video_id()` to be 11 alphanumeric+dash+underscore chars, which is good. However, the validation has a subtle issue (see next finding). If validation is bypassed, this becomes a command injection vector. Currently **mitigated by the list-form subprocess call** (no shell=True), so actual injection risk is low.

**Recommendation:** No immediate fix needed, but add an explicit re-validation assertion in `get_metadata()` as defense-in-depth.

---

### 🟡 MEDIUM — Video ID Extraction Has Edge Cases

**Location:** `utils.py:extract_video_id()`

1. The `qs['v'][0][:11]` truncation silently accepts IDs longer than 11 chars, potentially masking malformed input.
2. The bare-ID regex `r'^[\w-]{11}$'` uses `\w` which matches Unicode word chars (not just `[a-zA-Z0-9_]`). A crafted Unicode string of length 11 would pass validation. Unlikely to be exploitable but not strictly correct.
3. Dead code: lines 18-20 have a broken conditional (`if 'youtube.com' in parsed.hostname or '' if not parsed.hostname else '': pass`) — this is a no-op that does nothing but is confusing.

**Recommendation:** Use `r'^[a-zA-Z0-9_-]{11}$'` for the bare ID check. Remove the dead code. Validate length strictly instead of truncating.

---

### 🟢 LOW — Proxy Credentials in Environment Variable

**Location:** `extract.py:get_transcript_via_library()`

Proxy URL containing username:password is read from `YT_PROXY_URL` env var. This is the standard approach and acceptable, but the credentials are visible in the OpenClaw config (set via `gateway config.patch`). Anyone with access to the gateway config can read them.

**Recommendation:** Acceptable risk. Document that proxy credentials are stored in gateway config in plaintext.

---

### 🟢 LOW — Error Messages May Leak Internal Details

**Location:** `extract.py`, various `error()` calls

`error(f"Failed to get transcript: {e}")` could expose stack traces or internal paths. Similarly, `response.text[:200]` in API error handling leaks raw API response.

**Recommendation:** Sanitize error messages in production. Keep detailed errors for debug mode only.

---

### 🟢 LOW — `os.environ` Mutation as Config Passing

**Location:** `extract.py:main()`, line ~155

```python
if args.api_key:
    os.environ["TRANSCRIPT_API_KEY"] = args.api_key
```

Setting env vars at runtime is a code smell. It works but makes the code harder to reason about.

**Recommendation:** Pass the key as a function argument instead of mutating global state.

---

## 2. UX Findings

### 🔴 HIGH Priority — SKILL.md Has Contradictory Information

The SKILL.md mentions two completely different setups:
- **Description/Requirements:** Talks about Webshare proxy, `YT_PROXY_URL`, free static tier warnings
- **Workflow Step 1:** Uses `pass transcriptapi/api-key` and a paid TranscriptAPI.com service ($5/mo)
- **Error handling section:** References `SETUP_NEEDED` for IP blocks, Webshare setup flow
- **extract.py:** Has both paths — TranscriptAPI (primary) and youtube-transcript-api library (fallback)

**A new user would be thoroughly confused about which approach they need.** The SKILL.md reads as if it was partially migrated from the library-based approach to TranscriptAPI but the old instructions weren't fully cleaned up.

**Recommendation:** Decide on one primary narrative. If TranscriptAPI is the default, rewrite Requirements and Error Handling to lead with that. Keep the library fallback as a documented alternative.

---

### 🟡 MEDIUM Priority — `pass` Store Path Mismatch

SKILL.md says `pass transcriptapi/api-key` but TOOLS.md only documents `pass agentmail/api-key`. There's no instruction on how to set up the TranscriptAPI key in the password store.

**Recommendation:** Add setup instructions: `pass init --path transcriptapi <key1> <key2> && pass insert transcriptapi/api-key`

---

### 🟡 MEDIUM Priority — No Installation Instructions

The Notes section mentions `pip install youtube-transcript-api yt-dlp` but there's no clear "First Time Setup" section. A user finding this on ClawHub wouldn't know:
1. What Python version is needed
2. Whether to use pip or pipx
3. Whether these are pre-installed or need manual setup
4. How to get the TranscriptAPI key set up in `pass`

**Recommendation:** Add a "## Setup" section with numbered steps.

---

### 🟢 LOW Priority — Custom Prompt Discovery

The custom prompt feature (adding text alongside the URL) is only mentioned briefly in the description and workflow. A user wouldn't know they can do `https://youtu.be/xxx focus on the technical details` unless they read the full SKILL.md.

**Recommendation:** Add an example in the summary output footer, e.g., "💡 Tip: Add instructions after the URL to customize the summary."

---

## 3. ClawHub Readiness Gaps

### Frontmatter
- ✅ Has `name` and `description`
- ❌ Missing `version` field
- ❌ Missing `author` field
- ❌ Missing `tags` (e.g., `youtube, video, summary, transcript`)
- ❌ Missing `license`

### Documentation
- ❌ No `## Setup` section with clear first-run instructions
- ❌ Requirements section is contradictory (proxy vs API key)
- ❌ No changelog or version history
- ⚠️ The Notes section at the bottom feels like an afterthought

### Dependencies
- ⚠️ Python deps mentioned in Notes but not in a `requirements.txt`
- ❌ No `requirements.txt` file in the skill directory
- ❌ `requests` is used but not listed as a dependency

### Security for Publishing
- 🔴 The `--api-key` CLI pattern in SKILL.md would leak keys if anyone copies the workflow verbatim on a shared system
- ⚠️ The Webshare setup flow stores proxy credentials (including password) in gateway config — should be documented as a known limitation

---

## 4. Recommended Fixes (Priority Order)

1. **Rewrite SKILL.md for consistency** — Pick one primary path (TranscriptAPI vs library+proxy), make it the clear default, document the other as fallback. This is the biggest UX issue.

2. **Switch from `--api-key` CLI arg to env var** — Change SKILL.md workflow to `TRANSCRIPT_API_KEY="$(pass transcriptapi/api-key)" python3 extract.py "URL"`. Update `extract.py` to remove the `--api-key` argument entirely.

3. **Add frontmatter fields** — `version`, `author`, `tags`, `license`.

4. **Add `requirements.txt`** — `youtube-transcript-api`, `yt-dlp`, `requests`.

5. **Add `## Setup` section** — Clear numbered steps for first-time users.

6. **Fix dead code in `utils.py`** — Remove the broken conditional on lines 18-20.

7. **Tighten video ID validation** — Use ASCII-only regex, don't truncate silently.

8. **Remove `os.environ` mutation** — Pass API key as function argument through the call chain.
