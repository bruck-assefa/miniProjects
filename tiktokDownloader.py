import json
import os
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading


class TikTokDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TikTok Downloader")
        self.json_path = None
        self.categories = []
        self.links = []

        # UI Elements
        self.setup_initial_ui()

    def setup_initial_ui(self):
        # Clear existing UI
        for widget in self.root.winfo_children():
            widget.destroy()

        # Initial options
        tk.Label(self.root, text="Choose an action:", font=("Arial", 14)).pack(pady=20)
        tk.Button(self.root, text="Download Videos", command=self.setup_download_ui, width=20).pack(pady=10)
        tk.Button(self.root, text="Bake Metadata", command=self.setup_metadata_ui, width=20).pack(pady=10)

    def setup_download_ui(self):
        # Clear existing UI
        for widget in self.root.winfo_children():
            widget.destroy()

        # File selection
        file_frame = tk.Frame(self.root)
        file_frame.pack(pady=10)
        tk.Label(file_frame, text="Select TikTok JSON File:").pack(side=tk.LEFT)
        self.file_entry = tk.Entry(file_frame, width=40)
        self.file_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(file_frame, text="Browse", command=self.browse_file).pack(side=tk.LEFT)

        # Category selection
        self.category_listbox = tk.Listbox(self.root, selectmode=tk.MULTIPLE, height=10, width=50)
        self.category_listbox.pack(pady=10)

        # Scan button
        tk.Button(self.root, text="Scan JSON", command=self.scan_json).pack(pady=5)

        # Progress bar
        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=300, mode="determinate")
        self.progress.pack(pady=10)
        self.progress_label = tk.Label(self.root, text="")
        self.progress_label.pack()

        # Action buttons
        action_frame = tk.Frame(self.root)
        action_frame.pack(pady=10)
        tk.Button(action_frame, text="Download", command=self.start_download).pack(side=tk.LEFT, padx=5)
        tk.Button(action_frame, text="Back", command=self.setup_initial_ui).pack(side=tk.LEFT, padx=5)

        # Status
        self.status_label = tk.Label(self.root, text="", fg="green")
        self.status_label.pack(pady=10)

    def setup_metadata_ui(self):
        # Clear existing UI
        for widget in self.root.winfo_children():
            widget.destroy()

        # Folder selection
        folder_frame = tk.Frame(self.root)
        folder_frame.pack(pady=20)
        tk.Label(folder_frame, text="Select Folder Containing Videos and JSON Files:").pack(side=tk.LEFT)
        self.folder_entry = tk.Entry(folder_frame, width=40)
        self.folder_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(folder_frame, text="Browse", command=self.browse_folder).pack(side=tk.LEFT)

        # Progress bar
        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=300, mode="determinate")
        self.progress.pack(pady=20)
        self.progress_label = tk.Label(self.root, text="")
        self.progress_label.pack()

        # Action buttons
        action_frame = tk.Frame(self.root)
        action_frame.pack(pady=10)
        tk.Button(action_frame, text="Bake Metadata", command=self.start_metadata_embedding).pack(side=tk.LEFT, padx=5)
        tk.Button(action_frame, text="Back", command=self.setup_initial_ui).pack(side=tk.LEFT, padx=5)

        # Status
        self.status_label = tk.Label(self.root, text="", fg="green")
        self.status_label.pack(pady=10)

    def browse_file(self):
        self.json_path = filedialog.askopenfilename(
            title="Select TikTok JSON File", filetypes=[("JSON Files", "*.json")]
        )
        self.file_entry.delete(0, tk.END)
        self.file_entry.insert(0, self.json_path)

    def browse_folder(self):
        self.folder_path = filedialog.askdirectory(title="Select Folder")
        self.folder_entry.delete(0, tk.END)
        self.folder_entry.insert(0, self.folder_path)

    def scan_json(self):
        if not self.json_path or not os.path.exists(self.json_path):
            messagebox.showerror("Error", "Please select a valid JSON file.")
            return

        try:
            with open(self.json_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            activity = data.get("Activity", {})
            self.categories = [
                ("Like List", activity.get("Like List", {}).get("ItemFavoriteList", [])),
                ("Favorite Videos", activity.get("Favorite Videos", {}).get("FavoriteVideoList", [])),
                ("Video Browsing History", activity.get("Video Browsing History", {}).get("VideoList", [])),
            ]

            # Update the listbox with available categories
            self.category_listbox.delete(0, tk.END)
            for category, links in self.categories:
                self.category_listbox.insert(tk.END, f"{category} ({len(links)} links)")

            self.status_label.config(text="JSON scanned successfully. Select categories to download.")

        except json.JSONDecodeError:
            messagebox.showerror("Error", "Invalid JSON file format.")
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error: {e}")

    def start_download(self):
        selected_indices = self.category_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Warning", "Please select at least one category.")
            return

        # Collect links from the selected categories
        self.links = []
        for index in selected_indices:
            category, items = self.categories[index]
            self.links.extend(
                item.get("link") or item.get("Link") for item in items if item.get("link") or item.get("Link")
            )

        # Filter valid links
        self.links = [link for link in self.links if link.startswith("http")]
        if not self.links:
            messagebox.showinfo("Info", "No valid links found in the selected categories.")
            return

        result = messagebox.askyesno("Confirmation", f"Found {len(self.links)} links. Start downloading?")
        if result:
            threading.Thread(target=self.download_videos).start()

    def download_videos(self):
        output_dir = os.path.join("Videos")
        os.makedirs(output_dir, exist_ok=True)

        self.progress["value"] = 0
        self.progress["maximum"] = len(self.links)
        self.progress_label.config(text="Downloading videos...")

        for index, link in enumerate(self.links, start=1):
            output_template = os.path.join(output_dir, "%(id)s.%(ext)s")
            command = [
                "yt-dlp",
                "--cookies-from-browser", "Firefox",
                "-o", output_template,
                "--add-metadata",
                "--write-info-json",
                link,
            ]
            self.progress_label.config(text=f"Downloading video {index} of {len(self.links)}")
            self.status_label.config(text=f"Downloading video {index} of {len(self.links)}")
            self.root.update_idletasks()

            try:
                subprocess.run(command, check=True)
                self.progress["value"] = index
                self.root.update_idletasks()
            except subprocess.CalledProcessError:
                print(f"[ERROR] Failed to download video: {link}")

        self.status_label.config(text="All downloads completed. Embedding metadata...")
        threading.Thread(target=self.embed_metadata, args=(output_dir,)).start()

    def start_metadata_embedding(self):
        if not self.folder_path or not os.path.exists(self.folder_path):
            messagebox.showerror("Error", "Please select a valid folder.")
            return
        threading.Thread(target=self.embed_metadata, args=(self.folder_path,)).start()

    def embed_metadata(self, input_dir):
        output_dir = os.path.join(input_dir, "with_metadata")
        os.makedirs(output_dir, exist_ok=True)

        # Gather all .info.json files in the directory
        metadata_files = [f for f in os.listdir(input_dir) if f.endswith(".info.json")]
        self.progress["value"] = 0
        self.progress["maximum"] = len(metadata_files)
        self.progress_label.config(text="Embedding metadata into videos...")

        for index, metadata_file in enumerate(metadata_files, start=1):
            # Derive base name and corresponding video file
            base_name = metadata_file.rsplit(".info.json", 1)[0]  # Remove `.info.json`
            video_file = os.path.join(input_dir, f"{base_name}.mp4")
            json_file = os.path.join(input_dir, metadata_file)

            # Log the files being checked
            print(f"[INFO] Processing: {json_file}")
            print(f"[INFO] Expected video file: {video_file}")

            # Check if the video file exists
            if not os.path.exists(video_file):
                print(f"[WARN] Video file missing for JSON: {json_file}")
                continue

            # Read metadata from the JSON file
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                fulltitle = metadata.get("fulltitle", "Unknown Title")
                artist = metadata.get("artist", "Unknown Artist")
            except (FileNotFoundError, json.JSONDecodeError) as e:
                print(f"[WARN] Failed to read metadata from {json_file}: {e}")
                continue

            # Generate a short title and sanitized artist name for the output file
            short_title = fulltitle[:15].replace("/", "_").replace("\\", "_")
            sanitized_artist = artist.replace("/", "_").replace("\\", "_")
            output_file = os.path.join(output_dir, f"{sanitized_artist} - {short_title}.mp4")

            # FFmpeg command to embed metadata
            command = [
                "ffmpeg",
                "-y",
                "-i", video_file,
                "-metadata", f"title={fulltitle}",
                "-metadata", f"artist={artist}",
                "-codec", "copy",
                output_file,
            ]
            print(f"[INFO] Embedding metadata for: {video_file}")
            self.progress_label.config(text=f"Embedding metadata on video {index} of {len(metadata_files)}")
            self.status_label.config(text=f"Processing: {video_file}")
            self.progress["value"] = index
            self.root.update_idletasks()

            # Run the FFmpeg command
            try:
                subprocess.run(command, check=True)
            except subprocess.CalledProcessError as e:
                print(f"[ERROR] Failed to embed metadata for {video_file}: {e}")

        self.status_label.config(text="Metadata embedding completed.")
        self.progress_label.config(text="Done")




if __name__ == "__main__":
    root = tk.Tk()
    app = TikTokDownloaderApp(root)
    root.mainloop()
