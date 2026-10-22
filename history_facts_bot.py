"""
History Facts Auto Bot
=======================
Topic (khud AI chune ya aap den) -> Gemini se facts + har fact ke liye
image search query -> DuckDuckGo se asli history photos -> Hindi/Hinglish
awaaz -> ffmpeg se video (Shorts ya Long dono) -> YouTube upload.
Har stage par Telegram par status/error milta hai.
"""

import os
import re
import sys
import json
import time
import glob
import shutil
import asyncio
import logging
import subprocess

import requests
from PIL import Image, ImageDraw, ImageFont
import edge_tts
from gtts import gTTS
from ddgs import DDGS

from google import genai
from google.genai import types

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ==========================================
# CONFIGURATION
# ==========================================
GEMINI_API_KEYS = [
    os.getenv("GEMINI_API_KEY_1", "").strip(),
    os.getenv("GEMINI_API_KEY_2", "").strip(),
    os.getenv("GEMINI_API_KEY_3", "").strip(),
]
GEMINI_API_KEYS = [k for k in GEMINI_API_KEYS if k]
GEMINI_MODEL = os.getenv("GEMINI_MODEL_NAME", "gemini-3.6-flash")

GEMINI_CLIENTS = []
for idx, key in enumerate(GEMINI_API_KEYS, start=1):
    try:
        GEMINI_CLIENTS.append((f"KEY_{idx}", genai.Client(api_key=key)))
    except Exception as e:
        print(f"⚠️ GEMINI_API_KEY_{idx} client error: {e}")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
USED_TOPICS_FILE = "used_topics.txt"
OUTPUT_DIR = "bot_outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def notify_telegram(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML",
                  "disable_web_page_preview": False},
            timeout=20,
        )
    except Exception as e:
        logging.warning(f"⚠️ Telegram notify failed: {e}")


# ==========================================
# STEP 1: Content Generation (Gemini)
# ==========================================
def _call_gemini(prompt):
    """3 keys rotate karta hai, JSON return karta hai."""
    for key_label, gclient in GEMINI_CLIENTS:
        for attempt in range(1, 3):
            try:
                print(f"🔄 Gemini {key_label} Attempt {attempt}...")
                response = gclient.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json"),
                )
                raw_text = response.text.strip()
                clean = re.sub(r'^```json\s*|\s*```$', '', raw_text, flags=re.MULTILINE)
                return json.loads(clean)
            except Exception as e:
                print(f"⚠️ Gemini {key_label} Attempt {attempt} failed: {e}")
                time.sleep(2)
        notify_telegram(f"⚠️ Gemini {key_label} fail ho gayi, agli key try ho rahi hai...")
    return None


def generate_history_content(topic, video_format):
    n_facts = 3 if video_format == "shorts" else 7
    used_topics = ""
    if os.path.exists(USED_TOPICS_FILE):
        with open(USED_TOPICS_FILE, "r", encoding="utf-8") as f:
            used_topics = f.read().strip()

    if topic:
        topic_instruction = f'The topic MUST be: "{topic}".'
    else:
        topic_instruction = (
            "Choose ONE genuinely interesting, lesser-known History topic yourself "
            "(any country/era — Indian history, world wars, ancient civilizations, "
            "mysteries, etc). Do NOT repeat any of these already-used topics:\n"
            f"{used_topics if used_topics else '(none yet)'}"
        )

    if video_format == "shorts":
        structure_instruction = f"""
        This is for a SHORTS video (one single, focused story told in exactly {n_facts} short beats):
        - Beat 1 (HOOK): A punchy, curiosity-driven question or shocking claim in Hindi
          (e.g. "क्या आप जानते हैं कि...") — no fact detail yet, ONLY the hook, 15-20 words.
        - Beat 2 (THE FACT): The surprising core fact/detail itself, 30-40 words.
        - Beat 3 (TWIST/IMPACT): A closing punch line — the consequence, twist, or a one-line
          call to follow for more such facts, 15-25 words.
        All 3 beats must be about the SAME single event/person (not 3 random facts).
        """
    else:
        structure_instruction = f"""
        Write exactly {n_facts} DIFFERENT interesting facts about this topic, each 35-55 words.
        STRICT HOOK RULE: The very FIRST fact's text MUST start with a punchy, curiosity-driven
        HOOK line (a surprising question or shocking claim in Hindi, e.g. "क्या आप जानते हैं कि...")
        BEFORE getting into the fact detail. The remaining facts should each stand on their own.
        """

    prompt = f"""
    You are an expert viral YouTube scriptwriter for a Hindi "History Facts" channel.
    {topic_instruction}

    {structure_instruction}
    All text in natural spoken HINDI (Devanagari script), engaging and dramatic but factually
    reasonable (no fake statistics).

    For EACH beat/fact also give a SPECIFIC, SEARCHABLE ENGLISH image search query (5-10 words).
    Rules for image_query:
    - Must name the EXACT person / place / event / year / artifact mentioned in THAT beat.
    - Prefer queries that will find a real historical photograph, painting, portrait, statue, or
      monument (e.g. "Akbar the Great Mughal emperor portrait", "Battle of Plassey 1757 painting",
      "Taj Mahal Agra historical photo", "Ashoka pillar Sarnath").
    - NEVER use vague/abstract words alone: "map", "alliances", "power", "culture", "war", "army".
    - Make every query clearly DIFFERENT from the other facts so photos do not repeat.
    - Add words like "portrait", "painting", "photograph", "statue", "ruins", "manuscript" when helpful.

    Also give:
    - topic: the final topic name (English, short)
    - video_title: a clickable Hindi YouTube title for this topic (with emoji)
    - description: 2-3 line Hindi YouTube description with 5 hashtags
    - tags: array of 8-10 YouTube tags (English, mix of topic + "history facts" + "amazing facts")

    Return STRICT JSON only:
    {{
      "topic": "...",
      "video_title": "...",
      "description": "...",
      "tags": ["...", "..."],
      "facts": [
        {{"text": "हिंदी में तथ्य...", "image_query": "english search query"}}
      ]
    }}
    """
    data = _call_gemini(prompt)
    if not data or not data.get("facts"):
        notify_telegram("❌ History content generation fail ho gaya (Gemini).")
        return None

    if not topic and data.get("topic"):
        with open(USED_TOPICS_FILE, "a", encoding="utf-8") as f:
            f.write(data["topic"] + "\n")

    return data


# ==========================================
# STEP 2: Real photos (robust multi-source search)
# ==========================================
GENERIC_HISTORY_FALLBACKS = [
    "ancient history monument photograph",
    "old historical painting museum",
    "vintage historical photograph archive",
    "ancient civilization ruins photo",
    "old war photograph black and white",
    "historical manuscript illustration",
]

# Headers that look like a real browser (DDG/Bing sometimes block bare requests)
_IMG_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.bing.com/",
}


def _is_good_image_url(url: str) -> bool:
    """Skip obvious junk / non-photo links."""
    if not url or not url.startswith("http"):
        return False
    lower = url.lower()
    # Skip tiny icons, svg, data-uris, tracking pixels, etc.
    bad_bits = (
        ".svg", "data:image", "pixel", "spacer", "1x1", "blank.",
        "logo", "icon", "avatar", "favicon", "spinner", "loading",
    )
    if any(b in lower for b in bad_bits):
        return False
    return True


def _save_and_validate_image(content: bytes, out_path: str) -> bool:
    """Write bytes, open with PIL, force RGB JPEG, reject tiny/corrupt files."""
    try:
        with open(out_path, "wb") as f:
            f.write(content)
        img = Image.open(out_path)
        img.load()
        if img.width < 400 or img.height < 300:
            raise ValueError(f"Image too small: {img.width}x{img.height}")
        # Convert everything (WebP/PNG/CMYK/RGBA) to clean RGB JPEG
        img.convert("RGB").save(out_path, "JPEG", quality=90)
        return True
    except Exception as e:
        logging.debug(f"Image validate fail: {e}")
        try:
            if os.path.exists(out_path):
                os.remove(out_path)
        except Exception:
            pass
        return False


def _search_ddgs(query: str, max_results: int = 10):
    """
    Try multiple backends. ddgs library sometimes breaks on one backend
    while another still works.
    """
    backends = ["bing", "duckduckgo", None]  # None = library default
    all_results = []
    for backend in backends:
        try:
            with DDGS() as ddgs:
                kwargs = {"max_results": max_results}
                if backend:
                    kwargs["backend"] = backend
                results = list(ddgs.images(query, **kwargs))
            if results:
                all_results.extend(results)
                break  # first successful backend is enough
        except Exception as e:
            logging.warning(f"⚠️ DDGS backend={backend!r} fail for '{query}': {e}")
            time.sleep(1)
    return all_results


def _try_wikimedia(query: str, out_path: str) -> bool:
    """
    Free, high-quality historical images from Wikimedia Commons.
    No API key needed.
    """
    try:
        api = "https://commons.wikimedia.org/w/api.php"
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": f"filetype:bitmap {query}",
            "gsrlimit": 8,
            "gsrnamespace": 6,  # File namespace
            "prop": "imageinfo",
            "iiprop": "url|size|mime",
            "iiurlwidth": 1280,
        }
        r = requests.get(api, params=params, headers=_IMG_HEADERS, timeout=20)
        data = r.json()
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            info_list = page.get("imageinfo") or []
            if not info_list:
                continue
            info = info_list[0]
            url = info.get("thumburl") or info.get("url")
            if not url or not _is_good_image_url(url):
                continue
            # Prefer reasonably large files
            if info.get("size", 0) and info["size"] < 20000:
                continue
            try:
                res = requests.get(url, timeout=15, headers=_IMG_HEADERS)
                if res.status_code == 200 and len(res.content) > 15000:
                    if _save_and_validate_image(res.content, out_path):
                        logging.info(f"✅ Wikimedia image: {query}")
                        return True
            except Exception:
                continue
    except Exception as e:
        logging.warning(f"⚠️ Wikimedia search fail: {e}")
    return False


def download_image_for_fact(query, out_path, fallback_index=0, topic=""):
    """
    Robust image fetch for one history fact.
    Order:
      1. Exact image_query from Gemini (best relevance)
      2. query + "historical photograph" / "painting"
      3. topic-aware fallback
      4. Wikimedia Commons (high quality history images)
      5. Rotating generic history fallbacks
    """
    # Build a smart list of search queries (most specific first)
    queries = []
    if query:
        queries.append(query)
        # Slightly expanded versions often get better photo results
        queries.append(f"{query} historical photograph")
        queries.append(f"{query} painting")
    if topic:
        queries.append(f"{topic} historical")
        queries.append(f"{topic} history photograph")
    generic = GENERIC_HISTORY_FALLBACKS[fallback_index % len(GENERIC_HISTORY_FALLBACKS)]
    queries.append(generic)

    # Remove duplicates while keeping order
    seen = set()
    unique_queries = []
    for q in queries:
        q = (q or "").strip()
        if q and q.lower() not in seen:
            seen.add(q.lower())
            unique_queries.append(q)

    for attempt_no, q in enumerate(unique_queries):
        if attempt_no > 0:
            time.sleep(1.5)  # polite delay between searches

        # --- 1) DuckDuckGo / Bing ---
        results = _search_ddgs(q, max_results=10)
        for r in results:
            url = r.get("image") or r.get("thumbnail") or r.get("url")
            if not _is_good_image_url(url):
                continue
            try:
                res = requests.get(url, timeout=15, headers=_IMG_HEADERS, allow_redirects=True)
                if res.status_code == 200 and len(res.content) > 15000:
                    if _save_and_validate_image(res.content, out_path):
                        logging.info(f"✅ Image found via DDGS for: {q}")
                        return True
            except Exception:
                continue

        # --- 2) Wikimedia Commons (excellent for real history photos) ---
        if _try_wikimedia(q, out_path):
            return True

    logging.warning(f"❌ No usable image found for query='{query}' topic='{topic}'")
    return False


# ==========================================
# STEP 3: Voice (OpenAI.fm -> Edge TTS -> gTTS)
# ==========================================
def generate_voice_for_text(text, out_path):
    try:
        params = {"input": text, "voice": "fable",
                  "prompt": "Speak clearly in a natural, dramatic Hindi storyteller tone."}
        res = requests.get("https://www.openai.fm/api/generate", params=params, timeout=30)
        if res.status_code == 200 and len(res.content) > 4000:
            with open(out_path, "wb") as f:
                f.write(res.content)
            return True
    except Exception as e:
        logging.warning(f"⚠️ OpenAI.fm failed: {e}")

    try:
        async def _save():
            comm = edge_tts.Communicate(text, "hi-IN-MadhurNeural")
            await comm.save(out_path)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_save())
        loop.close()
        if os.path.exists(out_path) and os.path.getsize(out_path) > 4000:
            return True
    except Exception as e:
        logging.warning(f"⚠️ Edge TTS failed: {e}")

    try:
        gTTS(text=text, lang="hi").save(out_path)
        return os.path.exists(out_path) and os.path.getsize(out_path) > 4000
    except Exception as e:
        logging.error(f"❌ gTTS failed too: {e}")
        return False


def get_audio_duration(path):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, check=True
        )
        return float(out.stdout.strip())
    except Exception:
        return 5.0


# ==========================================
# STEP 4: Build the video
# ==========================================
def build_ken_burns_clip(image_path, duration, out_path, vertical=True):
    w, h = (1080, 1920) if vertical else (1920, 1080)
    zoompan = f"zoompan=z='min(zoom+0.0015,1.2)':d={int(duration*25)}:s={w}x{h}:fps=25"
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", image_path, "-t", str(duration),
        "-vf", f"scale={w*2}:{h*2}:force_original_aspect_ratio=increase,crop={w*2}:{h*2},{zoompan},format=yuv420p",
        "-c:v", "libx264", "-preset", "fast", out_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-800:])


def build_solid_fallback_clip(duration, out_path, vertical=True):
    """Agar image hi kharaab nikle, to crash hone ki jagah ek plain dark slide bana do."""
    w, h = (1080, 1920) if vertical else (1920, 1080)
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=0x202030:s={w}x{h}:d={duration}",
        "-c:v", "libx264", "-preset", "fast", out_path
    ]
    subprocess.run(cmd, capture_output=True, check=True)


def build_history_video(fact_items, video_format, output_path):
    """fact_items: list of {audio, image, duration, text}"""
    vertical = (video_format == "shorts")
    clips = []
    for i, item in enumerate(fact_items):
        clip_path = os.path.join(OUTPUT_DIR, f"clip_{i}.mp4")
        try:
            build_ken_burns_clip(item["image"], item["duration"], clip_path, vertical=vertical)
        except Exception as e:
            logging.warning(f"⚠️ Fact {i+1} ki photo se clip nahi bana ({e}), plain slide use ho rahi hai.")
            notify_telegram(f"⚠️ Fact {i+1} ki photo kharab thi, uski jagah plain slide use hui.")
            build_solid_fallback_clip(item["duration"], clip_path, vertical=vertical)

        # audio + subtitle burn-in
        final_clip = os.path.join(OUTPUT_DIR, f"final_{i}.mp4")
        safe_text = item["text"].replace("'", "").replace(":", "")[:200]
        drawtext = (
            f"drawtext=text='{safe_text}':fontcolor=white:fontsize=34:box=1:boxcolor=black@0.55:"
            f"boxborderw=14:x=(w-text_w)/2:y=h-th-140:line_spacing=8"
        )
        cmd = [
            "ffmpeg", "-y", "-i", clip_path, "-i", item["audio"],
            "-vf", f"{drawtext}", "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-c:a", "aac", "-shortest", final_clip
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Fact {i+1} final clip build fail: {result.stderr[-800:]}")
        clips.append(final_clip)

    list_file = os.path.join(OUTPUT_DIR, "concat_list.txt")
    with open(list_file, "w") as f:
        for c in clips:
            f.write(f"file '{os.path.abspath(c)}'\n")

    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
           "-c:v", "libx264", "-c:a", "aac", output_path]
    subprocess.run(cmd, capture_output=True, check=True)

    for f in clips + [list_file]:
        try:
            os.remove(f)
        except Exception:
            pass

    return os.path.exists(output_path)


# ==========================================
# STEP 5: YouTube Upload
# ==========================================
def upload_to_youtube(video_file, title, description, tags, is_short):
    try:
        SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        youtube = build("youtube", "v3", credentials=creds)

        final_title = title if not is_short else f"{title} #Shorts"
        body = {
            "snippet": {
                "title": final_title[:100],
                "description": description,
                "tags": tags,
                "categoryId": "27",  # Education
            },
            "status": {"privacyStatus": "public"}
        }
        media = MediaFileUpload(video_file, chunksize=-1, resumable=True, mimetype="video/mp4")
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        response = request.execute()
        video_id = response.get("id")
        video_url = f"https://youtu.be/{video_id}"
        print(f"✅ Uploaded: {video_url}")
        notify_telegram(f"✅ <b>History Facts video upload ho gaya!</b>\n🎬 {final_title}\n🔗 {video_url}")
        return video_url
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        notify_telegram(f"❌ <b>YouTube upload fail</b> ho gaya.\n<code>{e}</code>")
        return None


# ==========================================
# MAIN
# ==========================================
def main():
    topic = os.getenv("TOPIC", "").strip()
    video_format = os.getenv("VIDEO_FORMAT", "long").strip().lower()
    if video_format not in ("shorts", "long"):
        video_format = "long"

    notify_telegram(f"🚀 <b>History Facts video shuru hua</b>\nFormat: {video_format}\nTopic: {topic or '(AI khud chunega)'}")

    content = generate_history_content(topic, video_format)
    if not content:
        return

    fact_items = []
    for i, fact in enumerate(content["facts"]):
        img_path = os.path.join(OUTPUT_DIR, f"img_{i}.jpg")
        audio_path = os.path.join(OUTPUT_DIR, f"audio_{i}.mp3")

        if not download_image_for_fact(fact["image_query"], img_path, fallback_index=i, topic=content.get("topic", "")):
            notify_telegram(f"⚠️ Fact {i+1} ke liye koi photo nahi mili, plain slide use hogi.")

        if not generate_voice_for_text(fact["text"], audio_path):
            notify_telegram(f"❌ Fact {i+1} ki awaaz nahi ban payi.")
            return

        duration = get_audio_duration(audio_path) + 0.5
        fact_items.append({"image": img_path, "audio": audio_path, "duration": duration, "text": fact["text"]})

    video_file = os.path.join(OUTPUT_DIR, f"history_{int(time.time())}.mp4")
    if not build_history_video(fact_items, video_format, video_file):
        notify_telegram("❌ Video build (ffmpeg) fail ho gaya.")
        return

    upload_to_youtube(
        video_file, content["video_title"], content["description"], content["tags"],
        is_short=(video_format == "shorts")
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        notify_telegram(f"❌ <b>Automation CRASH ho gaya</b>\n<code>{e}</code>")
        raise
