#!/usr/bin/env python3
"""Extract YouTube video transcript and metadata. Supports TranscriptAPI.com or local fallback."""

import argparse
import json
import os
import subprocess
import sys
from typing import Optional

import requests
import re as regex
from utils import extract_video_id, count_tokens_approx, format_duration

# Error messages
SETUP_NEEDED_MESSAGE = """SETUP_NEEDED: No transcript service configured.

To enable YouTube transcripts, sign up at https://transcriptapi.com ($5/mo for 1,000 transcripts).
Once you have an API key, I can walk you through setting it up."""

API_ERROR_MESSAGE = """API_ERROR: TranscriptAPI returned an error. Check your API key and try again."""


def progress(msg: str):
    print(f"PROGRESS: {msg}", flush=True)


def error(msg: str):
    print(f"ERROR: {msg}", flush=True)
    sys.exit(1)


def get_metadata(video_id: str) -> dict:
    """Fetch video metadata via oEmbed (primary) or yt-dlp (fallback)."""
    # Primary: oEmbed (no auth, different endpoint - often works even when yt-dlp is blocked)
    try:
        r = requests.get(
            "https://www.youtube.com/oembed",
            params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            return {
                "title": data.get("title", "Unknown"),
                "channel": data.get("author_name", "Unknown"),
                "duration": 0,  # oEmbed doesn't provide duration
            }
    except Exception:
        pass

    # Fallback: yt-dlp (will fail on VPS with blocked IP)
    try:
        r = subprocess.run(
            ["yt-dlp", "--dump-json", "--no-download", f"https://www.youtube.com/watch?v={video_id}"],
            capture_output=True, text=True, timeout=30
        )
        if r.returncode == 0:
            data = json.loads(r.stdout)
            return {
                "title": data.get("title", "Unknown"),
                "channel": data.get("channel", data.get("uploader", "Unknown")),
                "duration": data.get("duration", 0),
            }
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        pass
    
    return {"title": None, "channel": None, "duration": 0}


def get_transcript_via_api(video_id: str, api_key: str) -> tuple[str, str]:
    """Fetch transcript via TranscriptAPI.com."""
    url = "https://transcriptapi.com/api/v2/youtube/transcript"
    params = {
        "video_url": video_id,
        "format": "json",
        "include_timestamp": "false",  # We just want plain text
    }
    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        
        if response.status_code == 401:
            error("API_ERROR: Invalid API key. Check your TranscriptAPI key.")
        elif response.status_code == 429:
            error("API_ERROR: Rate limited. Wait a moment and try again.")
        elif response.status_code != 200:
            error(f"API_ERROR: HTTP {response.status_code} - {response.text[:200]}")
        
        data = response.json()
        
        # Parse response: {title, duration, transcript: [{text}]}
        title = data.get("title", "Unknown")
        duration_str = data.get("duration", "unknown")
        
        # Combine all segments into one text
        transcript_array = data.get("transcript", [])
        transcript_text = " ".join(seg.get("text", "") for seg in transcript_array)
        
        # Detect language (TranscriptAPI doesn't give this directly, default to English)
        # Could parse from segments if needed
        language = "en"
        
        return transcript_text, language

    except requests.exceptions.Timeout:
        error("API_ERROR: Request timed out. Try again.")
    except requests.exceptions.RequestException as e:
        error(f"API_ERROR: Network error - {e}")
    except json.JSONDecodeError:
        error("API_ERROR: Invalid response from API.")


def get_transcript_via_library(video_id: str) -> tuple[str, str]:
    """Fetch transcript via youtube-transcript-api (fallback for local dev)."""
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api.proxies import GenericProxyConfig, WebshareProxyConfig

    proxy_url = os.environ.get("YT_PROXY_URL")
    
    try:
        if proxy_url:
            # Try WebshareProxyConfig with credentials
            m = regex.match(r"https?://([^:]+):([^@]+)@", proxy_url)
            if m:
                user, pwd = m.group(1), m.group(2)
                api = YouTubeTranscriptApi(
                    proxy_config=WebshareProxyConfig(proxy_username=user, proxy_password=pwd)
                )
            else:
                api = YouTubeTranscriptApi(
                    proxy_config=GenericProxyConfig(http_url=proxy_url, https_url=proxy_url)
                )
        else:
            api = YouTubeTranscriptApi()

        transcript_list = api.list(video_id)
        
        # Find a transcript
        transcript = None
        detected_lang = "en"
        
        # Prefer manual over auto-generated
        for t in transcript_list:
            if not t.is_generated:
                transcript = t
                detected_lang = t.language_code
                break
        
        if not transcript:
            # Fall back to any transcript
            for t in transcript_list:
                transcript = t
                detected_lang = t.language_code
                break
        
        if not transcript:
            error("No transcript available for this video.")

        fetched = transcript.fetch()
        text = " ".join(snippet.text for snippet in fetched)
        return text, detected_lang

    except Exception as e:
        err_str = str(e).lower()
        if "blocking requests from your ip" in err_str or "request blocked" in err_str:
            error(SETUP_NEEDED_MESSAGE)
        error(f"Failed to get transcript: {e}")


def get_transcript(video_id: str) -> tuple[str, str]:
    """Main entry point - uses TranscriptAPI if available, falls back to library."""
    api_key = os.environ.get("TRANSCRIPT_API_KEY")
    
    if api_key:
        return get_transcript_via_api(video_id, api_key)
    else:
        # Fall back to local library (for dev/testing without API key)
        return get_transcript_via_library(video_id)


def main():
    parser = argparse.ArgumentParser(description="Extract YouTube video transcript and metadata")
    parser.add_argument("video", help="YouTube URL or video ID")
    parser.add_argument("--lang", help="Preferred transcript language (ignored for API)", default=None)
    parser.add_argument("--api-key-file", help="Path to file containing TranscriptAPI key", default=None)
    args = parser.parse_args()

    # Read API key from file if provided, otherwise fall back to env var
    if args.api_key_file:
        try:
            with open(args.api_key_file) as f:
                os.environ["TRANSCRIPT_API_KEY"] = f.read().strip()
        except OSError as e:
            error(f"Cannot read API key file: {e}")

    try:
        video_id = extract_video_id(args.video)
    except ValueError as e:
        error(str(e))

    progress(f"🔍 Fetching video info for {video_id}...")

    meta = get_metadata(video_id)
    duration_s = meta["duration"]
    duration_str = format_duration(duration_s) if duration_s else "unknown length"

    if duration_s > 7200:
        progress("⚠️ This video is over 2 hours — processing may take a while.")

    progress("📝 Extracting transcript...")
    transcript, detected_lang = get_transcript(video_id)
    tokens = count_tokens_approx(transcript)

    progress(f"📺 Got transcript ({duration_str}, ~{tokens} tokens).")

    # Output structured JSON result
    output = {
        "video_id": video_id,
        "title": meta["title"],
        "channel": meta["channel"],
        "duration": duration_s,
        "duration_str": duration_str,
        "language": detected_lang,
        "tokens": tokens,
        "transcript": transcript,
    }

    # Build header
    header_parts = []
    if meta["title"]:
        header_parts.append(f'📺 **{meta["title"]}**')
        if meta["channel"]:
            header_parts.append(f' — {meta["channel"]}')
        if duration_s:
            header_parts.append(f' ({duration_str})')
        output["header"] = ''.join(header_parts)
    else:
        output["header"] = f"📺 Video {video_id}"

    print(f"RESULT: {json.dumps(output)}", flush=True)


if __name__ == "__main__":
    main()
