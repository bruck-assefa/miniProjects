import os
import sys
import json
import subprocess
import signal

# ---------- Configuration ----------
USER_HISTORY_JSON = 'user_data_tiktok.json'
OUTPUT_DIR = os.path.join('TikTok', 'TikTok', 'Videos')
WITH_METADATA_DIR = os.path.join('TikTok', 'with_metadata')
LINKS_PER_CHUNK = 130  # Adjust as needed
BASE_COMMAND = (
    'yt-dlp '
    '--cookies-from-browser Firefox '
    f'-o "{os.path.join(OUTPUT_DIR, "%(id)s.%(ext)s")}" '
    '--add-metadata '
    '--write-info-json '
)
JQ_PATH = 'jq.exe'  # Replace with the full path to jq.exe if not in PATH
FFMPEG_PATH = 'ffmpeg.exe'  # Replace with the full path to ffmpeg.exe if not in PATH

# ---------- Helper Functions ----------
def read_links_from_history(json_path):
    """
    Reads a TikTok user history JSON file and extracts the "Like List" links.
    """
    with open(json_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    like_list = data.get("Activity", {}).get("Like List", {}).get("ItemFavoriteList", [])
    links = [item.get("link") for item in like_list if item.get("link")]
    return links

def chunk_list(lst, chunk_size):
    """
    Splits a list into chunks of given size.
    """
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]

def run_command(command):
    """
    Runs a shell command with subprocess.run and handles Ctrl+C cancellation.
    """
    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}: {command}")
    except KeyboardInterrupt:
        print("Operation cancelled by user.")
        sys.exit(1)

def sanitize_filename(filename):
    """
    Removes or replaces characters that may be problematic in Windows filenames.
    """
    forbidden_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for ch in forbidden_chars:
        filename = filename.replace(ch, '_')
    return filename

def embed_metadata(input_mp4, input_json, output_dir):
    """
    Embeds metadata from the JSON into the MP4 video using FFmpeg & jq.
    """
    try:
        # Extract metadata using jq
        fulltitle_cmd = f'{JQ_PATH} -r ".fulltitle" "{input_json}"'
        artist_cmd = f'{JQ_PATH} -r ".artist" "{input_json}"'

        fulltitle = subprocess.check_output(fulltitle_cmd, shell=True, text=True).strip()
        artist = subprocess.check_output(artist_cmd, shell=True, text=True).strip()
    except subprocess.CalledProcessError:
        print(f"[WARN] Could not extract metadata from {input_json}. Skipping.")
        return

    # Sanitize and truncate title
    short_title = sanitize_filename(fulltitle[:15])
    safe_artist = sanitize_filename(artist)

    # Construct output filename
    output_filename = f"{safe_artist} - {short_title}.mp4"
    output_path = os.path.join(output_dir, output_filename)

    # Embed metadata with FFmpeg
    ffmpeg_cmd = (
        f'{FFMPEG_PATH} -y -i "{input_mp4}" '
        f'-metadata title="{fulltitle}" '
        f'-metadata artist="{artist}" '
        f'-codec copy "{output_path}"'
    )
    try:
        run_command(ffmpeg_cmd)
        print(f"[INFO] Metadata embedded -> {output_path}")
    except KeyboardInterrupt:
        print("[INFO] Cancelled during FFmpeg processing.")
        sys.exit(1)

# ---------- Main Download & Metadata Flow ----------
def main():
    # Ensure directories exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(WITH_METADATA_DIR, exist_ok=True)

    # Read TikTok links from history
    print("[INFO] Reading user history JSON...")
    links = read_links_from_history(USER_HISTORY_JSON)
    total_links = len(links)
    print(f"[INFO] Found {total_links} liked video links.")

    if total_links == 0:
        print("[INFO] No links found. Exiting.")
        return

    # Chunk links
    chunks = list(chunk_list(links, LINKS_PER_CHUNK))
    print(f"[INFO] Total chunks: {len(chunks)}")

    # Download videos
    for i, chunk in enumerate(chunks, start=1):
        print(f"[INFO] Downloading chunk {i}/{len(chunks)}...")
        links_part = " ".join(f'"{link}"' for link in chunk)
        command = BASE_COMMAND + " " + links_part
        print(f"[CMD] Running yt-dlp for chunk {i}...")
        run_command(command)

    print("[INFO] All downloads completed.")

    # Embed metadata
    print("[INFO] Embedding metadata into videos...")
    for file in os.listdir(OUTPUT_DIR):
        if file.endswith('.info.json'):
            base_name = file[:-9]  # Remove .info.json
            mp4_file = os.path.join(OUTPUT_DIR, f"{base_name}.mp4")
            json_file = os.path.join(OUTPUT_DIR, file)

            if os.path.exists(mp4_file):
                embed_metadata(mp4_file, json_file, WITH_METADATA_DIR)
            else:
                print(f"[WARN] MP4 file missing for JSON: {json_file}")

    print("[INFO] Metadata embedding completed.")

if __name__ == "__main__":
    def signal_handler(sig, frame):
        print("\n[INFO] Exiting gracefully.")
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)

    main()
