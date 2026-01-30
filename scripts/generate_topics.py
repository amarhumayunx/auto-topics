#!/usr/bin/env python3
"""
GitHub Auto Topics Manager (AI Powered)
Reads repo files (README, package.json, pubspec.yaml, etc.),
detects tech stack, generates smart topics via OpenAI, updates via GitHub API.
"""
import os
import re
import requests
from openai import OpenAI

# --- Config (use env vars; set in GitHub Secrets: GH_TOKEN, OPENAI_API_KEY) ---
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
GH_TOKEN = os.getenv("GH_TOKEN")
HEADERS = {
    "Authorization": f"token {GH_TOKEN}",
    "Accept": "application/vnd.github+json",
}
# Topics API needs this Accept header
TOPICS_HEADERS = {
    **HEADERS,
    "Accept": "application/vnd.github.mercy-preview+json",
}

# Only update repos that have no topics (set False to always update)
ONLY_UPDATE_IF_TOPICS_EMPTY = True

MAX_CONTENT_LENGTH = 4000  # chars sent to AI


def get_repos():
    """Fetch all repos for the authenticated user (first page)."""
    r = requests.get(
        "https://api.github.com/user/repos?per_page=100&sort=updated",
        headers=HEADERS,
    )
    r.raise_for_status()
    return r.json()


def get_file_content(owner, repo, path):
    """Get raw content of a file from GitHub (main branch)."""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    r = requests.get(url, headers=HEADERS)
    if r.status_code != 200:
        return ""
    data = r.json()
    if data.get("encoding") == "base64":
        import base64
        return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    return ""


def get_readme(owner, repo):
    """Get README content (any of README, README.md, etc.)."""
    url = f"https://api.github.com/repos/{owner}/{repo}/readme"
    r = requests.get(url, headers=HEADERS)
    if r.status_code != 200:
        return ""
    return requests.get(r.json()["download_url"]).text


def get_repo_content(owner, repo):
    """Build a single blob of content from README + package.json / pubspec / requirements etc."""
    parts = []

    readme = get_readme(owner, repo)
    if readme:
        parts.append(f"## README\n{readme}")

    for path in ("package.json", "pubspec.yaml", "requirements.txt", "Cargo.toml", "go.mod"):
        content = get_file_content(owner, repo, path)
        if content:
            parts.append(f"## {path}\n{content}")

    return "\n\n".join(parts)[:MAX_CONTENT_LENGTH]


def get_current_topics(owner, repo):
    """Get existing topics for a repo."""
    url = f"https://api.github.com/repos/{owner}/{repo}/topics"
    r = requests.get(url, headers=TOPICS_HEADERS)
    if r.status_code != 200:
        return []
    return r.json().get("names", [])


def generate_topics(content, repo_name):
    """Use OpenAI to generate 5–8 lowercase, hyphenated GitHub topics."""
    prompt = f"""
Analyze this repository and generate 5–8 GitHub topics.
Rules:
- Only lowercase, hyphenated keywords (e.g. flutter, react-native, machine-learning).
- Include tech stack (language, framework) and domain (e.g. cli-tool, api, mobile-app).
- No spaces; use hyphens. No hashtags or extra symbols.
- Repo name for context: {repo_name}

Content:
{content}
"""
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    raw = res.choices[0].message.content.strip()
    # Parse comma/newline separated list, normalize
    topics = []
    for t in re.split(r"[\n,]", raw):
        t = t.strip().lower().replace(" ", "-").replace("_", "-")
        t = re.sub(r"[^a-z0-9-]", "", t)
        if t and len(t) <= 50:
            topics.append(t)
    return topics[:8]  # max 8


def update_topics(owner, repo, topics):
    """Replace repo topics via GitHub API."""
    url = f"https://api.github.com/repos/{owner}/{repo}/topics"
    r = requests.put(url, headers=TOPICS_HEADERS, json={"names": topics})
    r.raise_for_status()


def main():
    if not GH_TOKEN or not os.getenv("OPENAI_API_KEY"):
        print("Missing GH_TOKEN or OPENAI_API_KEY. Add them in GitHub Secrets.")
        return

    repos = get_repos()
    print(f"Found {len(repos)} repo(s).")

    for repo in repos:
        owner = repo["owner"]["login"]
        name = repo["name"]
        private = repo.get("private", False)

        content = get_repo_content(owner, name)
        if not content.strip():
            print(f"⏭ Skipped {name} (no README or config files)")
            continue

        if ONLY_UPDATE_IF_TOPICS_EMPTY:
            current = get_current_topics(owner, name)
            if current:
                print(f"⏭ Skipped {name} (already has topics: {current})")
                continue

        topics = generate_topics(content, name)
        if not topics:
            print(f"⚠ No topics generated for {name}")
            continue

        try:
            update_topics(owner, name, topics)
            print(f"✅ Updated topics for {name}: {topics}")
        except requests.RequestException as e:
            print(f"❌ Failed {name}: {e}")


if __name__ == "__main__":
    main()
