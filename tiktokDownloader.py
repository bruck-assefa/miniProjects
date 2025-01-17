import json
import os
import subprocess
import sys


def read_likes_from_history(json_path):
    """
    Reads a TikTok user history JSON file and extracts links from the 'Like List' section.
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"[ERROR] JSON file not found: {json_path}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"[ERROR] Invalid JSON file format: {json_path}")
        sys.exit(1)

    # Navigate to the "Like List" -> "ItemFavoriteList" -> "link"
    like_list = data.get("Activity", {}).get("Like List", {}).get("ItemFavoriteList", [])
    links = [item.get("link") for item in like_list if item.get("link")]

    if links:
        print(f"[INFO] Found {len(links)} liked video links.")
    else:
        print("[WARN] No liked video links found in the 'Like List' section.")

    return links


def download_videos(links, output_dir, max_downloads=None):
    """
    Downloads TikTok videos using yt-dlp and saves them to the specified directory.
    """
    os.makedirs(output_dir, exist_ok=True)

    if max_downloads:
        links = links[:max_downloads]

    print(f"[INFO] Preparing to download {len(links)} videos...")

    for index, link in enumerate(links, start=1):
        output_template = os.path.join(output_dir, "%(id)s.%(ext)s")
        command = [
            "yt-dlp",
            "--cookies-from-browser", "Firefox",
            "-o", output_template,
            "--add-metadata",
            "--write-info-json",
            link,
        ]
        print(f"[INFO] Downloading video {index}/{len(links)}: {link}")
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError:
            print(f"[ERROR] Failed to download video: {link}")
        except KeyboardInterrupt:
            print("\n[INFO] Operation cancelled by user.")
            sys.exit(0)

    print("[INFO] All downloads completed.")


def embed_metadata(input_dir, output_dir):
    """
    Embeds metadata from the JSON into the MP4 videos using FFmpeg.
    """
    os.makedirs(output_dir, exist_ok=True)

    for file in os.listdir(input_dir):
        if file.endswith(".info.json"):
            base_name = file[:-9]  # Remove .info.json
            video_file = os.path.join(input_dir, f"{base_name}.mp4")
            json_file = os.path.join(input_dir, file)

            if not os.path.exists(video_file):
                print(f"[WARN] Video file missing for JSON: {json_file}")
                continue

            # Extract metadata from JSON
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                fulltitle = metadata.get("fulltitle", "Unknown Title")
                artist = metadata.get("artist", "Unknown Artist")
            except (FileNotFoundError, json.JSONDecodeError):
                print(f"[WARN] Failed to read metadata from: {json_file}")
                continue

            # Construct sanitized filename for output
            short_title = fulltitle[:15].replace("/", "_").replace("\\", "_")
            sanitized_artist = artist.replace("/", "_").replace("\\", "_")
            output_file = os.path.join(output_dir, f"{sanitized_artist} - {short_title}.mp4")

            # FFmpeg command to embed metadata
            command = [
                "ffmpeg",
                "-y",  # Overwrite output file if it exists
                "-i", video_file,
                "-metadata", f"title={fulltitle}",
                "-metadata", f"artist={artist}",
                "-codec", "copy",
                output_file,
            ]
            print(f"[INFO] Embedding metadata for: {video_file}")
            try:
                subprocess.run(command, check=True)
                print(f"[INFO] Metadata embedded: {output_file}")
            except subprocess.CalledProcessError:
                print(f"[ERROR] Failed to embed metadata for: {video_file}")
            except KeyboardInterrupt:
                print("\n[INFO] Operation cancelled by user.")
                sys.exit(0)


def main():
    json_path = "user_data_tiktok.json"  # Path to the JSON file
    input_dir = os.path.join("TikTok", "Videos")  # Directory for downloaded videos
    output_dir = os.path.join("TikTok", "with_metadata")  # Directory for videos with metadata
    max_downloads = 5  # Set this to limit downloads during testing; use None for no limit

    print("[INFO] Extracting liked video links...")
    links = read_likes_from_history(json_path)

    if not links:
        print("[INFO] No links to download. Exiting.")
        return

    # Step 1: Download videos
    download_videos(links, input_dir, max_downloads)

    # Step 2: Embed metadata
    print("[INFO] Embedding metadata into videos...")
    embed_metadata(input_dir, output_dir)

    print("[INFO] All operations completed successfully.")


if __name__ == "__main__":
    main()
