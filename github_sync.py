#!/usr/bin/env python3
"""
github_sync.py - GitHub er langtidsminnet
Synkroniserer lokal minnebase med GitHub-repoet automatisk.
Repoet tussienorway/gemini-minne ER hjernen din på skyen.
"""

import os
import json
import base64
import datetime
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    raise ImportError("Kjør: pip install requests")

GITHUB_TOKEN  = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO   = os.environ.get("GITHUB_REPO", "tussienorway/gemini-minne")
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main")
MEMORY_DIR    = Path(os.environ.get("MEMORY_DIR", "./minne"))


class GitHubSync:
    """Synkroniserer minne til/fra GitHub automatisk."""

    def __init__(self):
        self.token  = GITHUB_TOKEN
        self.repo   = GITHUB_REPO
        self.branch = GITHUB_BRANCH
        self.api    = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept"       : "application/vnd.github.v3+json",
            "Content-Type" : "application/json",
        }

    def _get_file(self, path: str) -> Optional[dict]:
        """Henter en fil fra GitHub."""
        url = f"{self.api}/repos/{self.repo}/contents/minne/{path}"
        r   = requests.get(url, headers=self.headers, params={"ref": self.branch})
        if r.status_code == 200:
            return r.json()
        return None

    def _put_file(self, path: str, content: str, message: str = None) -> bool:
        """Laster opp/oppdaterer en fil på GitHub."""
        url     = f"{self.api}/repos/{self.repo}/contents/minne/{path}"
        encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        msg     = message or f"[auto-minne] Oppdatert {path} {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        payload = {"message": msg, "content": encoded, "branch": self.branch}
        # Sjekk om filen finnes (trenger SHA for oppdatering)
        existing = self._get_file(path)
        if existing:
            payload["sha"] = existing["sha"]
        r = requests.put(url, headers=self.headers, json=payload)
        return r.status_code in (200, 201)

    def push_memory(self, local_path: Path, remote_path: str = None) -> bool:
        """Pusher en lokal minnefil til GitHub."""
        if not local_path.exists():
            return False
        remote = remote_path or local_path.name
        content = local_path.read_text(encoding="utf-8")
        ok = self._put_file(remote, content)
        if ok:
            print(f"[GitHub] Pushet: {remote}")
        else:
            print(f"[GitHub] FEIL ved push: {remote}")
        return ok

    def pull_memory(self, remote_path: str, local_path: Path) -> bool:
        """Henter en minnefil fra GitHub til lokalt."""
        data = self._get_file(remote_path)
        if not data:
            return False
        content = base64.b64decode(data["content"]).decode("utf-8")
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_text(content, encoding="utf-8")
        print(f"[GitHub] Hentet: {remote_path}")
        return True

    def sync_all(self, memory_dir: Path = None) -> dict:
        """
        Synkroniserer ALLE minnefiler automatisk.
        Pusher alt fra lokal minnebase til GitHub.
        """
        base = memory_dir or MEMORY_DIR
        results = {"ok": [], "feil": []}
        if not base.exists():
            print("[GitHub] Ingen lokal minnebase funnet.")
            return results
        for f in base.rglob("*.json"):
            rel = f.relative_to(base)
            ok  = self.push_memory(f, str(rel))
            (results["ok"] if ok else results["feil"]).append(str(rel))
        print(f"[GitHub] Sync ferdig: {len(results['ok'])} ok, {len(results['feil'])} feil")
        return results

    def restore_all(self, memory_dir: Path = None) -> int:
        """
        Gjenoppretter alle minnefiler fra GitHub.
        Brukes ved første oppstart eller ved å miste data.
        """
        base  = memory_dir or MEMORY_DIR
        count = 0
        url   = f"{self.api}/repos/{self.repo}/git/trees/{self.branch}?recursive=1"
        r     = requests.get(url, headers=self.headers)
        if r.status_code != 200:
            print("[GitHub] Kunne ikke hente filtre.")
            return 0
        tree = r.json().get("tree", [])
        for item in tree:
            p = item["path"]
            if p.startswith("minne/") and p.endswith(".json"):
                rel   = p[len("minne/"):]
                local = base / rel
                if self.pull_memory(rel, local):
                    count += 1
        print(f"[GitHub] Gjenopprettet {count} minnefiler.")
        return count

    def log_session(self, summary: str) -> bool:
        """Logger en samtale-session til GitHub."""
        ts   = datetime.datetime.now().strftime("%Y/%m/%d_%H%M%S")
        path = f"episodisk/{ts}.json"
        data = json.dumps({
            "timestamp": datetime.datetime.now().isoformat(),
            "summary"  : summary,
        }, ensure_ascii=False, indent=2)
        return self._put_file(path, data, f"[session] {ts}")

    def is_configured(self) -> bool:
        """Sjekker om GitHub er konfigurert."""
        return bool(self.token and self.repo)

    def test_connection(self) -> bool:
        """Tester GitHub-tilkoblingen."""
        url = f"{self.api}/repos/{self.repo}"
        r   = requests.get(url, headers=self.headers)
        ok  = r.status_code == 200
        print(f"[GitHub] Tilkobling: {'OK' if ok else 'FEIL (' + str(r.status_code) + ')'}")
        return ok
