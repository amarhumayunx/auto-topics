# GitHub Auto Topics Manager (AI Powered)

One-time setup, then fully automatic: reads repo files (README, package.json, pubspec.yaml, etc.), detects tech stack, generates smart topics via AI, and updates repo topics via GitHub API.

## Setup

### 1. GitHub Token

- **GitHub** → **Settings** → **Developer settings** → **Personal access tokens (classic)**
- Create token with scope: **`repo`**
- Copy the token

### 2. Add Secrets

- This repo (or your org) → **Settings** → **Secrets and variables** → **Actions**
- Add:
  - **`GH_TOKEN`** → your GitHub token
  - **`OPENAI_API_KEY`** → your OpenAI API key

### 3. Run

- **Manual:** **Actions** → **Auto Update Repo Topics** → **Run workflow**
- **Automatic:** Runs every Monday at 3:00 UTC

## Repo structure

```
.github/workflows/auto-topics.yml   # workflow
scripts/generate_topics.py          # AI script
```

## Behavior

- Fetches your repos (first 100, sorted by updated).
- For each repo: reads README + `package.json` / `pubspec.yaml` / `requirements.txt` / `Cargo.toml` / `go.mod` if present.
- Sends content to OpenAI (gpt-4o-mini) to generate 5–8 lowercase, hyphenated topics.
- By default **only updates repos that have no topics** (set `ONLY_UPDATE_IF_TOPICS_EMPTY = False` in the script to always update).

## Local run

```bash
pip install -r requirements.txt
export GH_TOKEN=your_github_token
export OPENAI_API_KEY=your_openai_key
python scripts/generate_topics.py
```
