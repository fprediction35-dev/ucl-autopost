"""Puts a video at a public URL (Instagram downloads Reels from a URL). Uses a GitHub Release on this repository."""
import os, subprocess, json


def publish(video, date):
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        raise RuntimeError("Public video hosting needs GitHub Actions (GITHUB_REPOSITORY not set)")
    tag = f"videos-{date}"
    if subprocess.run(["gh", "release", "view", tag], capture_output=True).returncode != 0:
        subprocess.run(["gh", "release", "create", tag, "--title", f"Videos {date}", "--notes", "Auto-generated match simulations"], check=True)
    subprocess.run(["gh", "release", "upload", tag, video, "--clobber"], check=True)
    return f"https://github.com/{repo}/releases/download/{tag}/{os.path.basename(video)}"
