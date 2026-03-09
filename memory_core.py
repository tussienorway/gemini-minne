#!/usr/bin/env python3
"""
memory_core.py - Hjernen i gemini-minne
Fotografisk hukommelse: lagrer ALT automatisk, strukturert som en menneskelig hjerne.

Lag:
  - Sensorisk minne   : rå input (siste sekunder)
  - Korttidsminne     : aktiv kontekst (siste N meldinger)
  - Langtidsminne     : permanent lagring (lokalt JSON + GitHub)
  - Semantisk indeks  : vektorlignende nøkkelord-søk
"""

import json
import os
import re
import hashlib
import datetime
from pathlib import Path
from typing import Any, Optional

MEMORY_DIR = Path(os.environ.get("MEMORY_DIR", "./minne"))
SHORT_TERM_SIZE = int(os.environ.get("SHORT_TERM_SIZE", "20"))


class MemoryCore:
    """Fotografisk hukommelse - fungerer som en menneskelig hjerne."""

    def __init__(self):
        self.memory_dir = MEMORY_DIR
        self._setup_dirs()
        self.sensory    = []          # Sensorisk minne (flyktig)
        self.short_term = self._load_short_term()  # Korttidsminne
        self.long_term  = self._load_long_term()   # Langtidsminne
        self.index      = self._build_index()      # Semantisk indeks

    def _setup_dirs(self):
        for sub in ["korttid", "langtid", "episodisk", "semantisk", "prosedyre"]:
            (self.memory_dir / sub).mkdir(parents=True, exist_ok=True)

    # ---------- LAGRING ----------

    def remember(self, content: str, meta: dict = None) -> str:
        """Lagrer et minne automatisk - ingen manuell jobb."""
        ts  = datetime.datetime.now().isoformat()
        uid = hashlib.md5((content + ts).encode()).hexdigest()[:8]
        entry = {
            "id"       : uid,
            "timestamp": ts,
            "content"  : content,
            "meta"     : meta or {},
            "tags"     : self._extract_tags(content),
            "importance": self._score_importance(content),
        }

        # 1. Sensorisk minne (RAM - flyktig)
        self.sensory.append(entry)
        if len(self.sensory) > 5:
            self.sensory.pop(0)

        # 2. Korttidsminne
        self.short_term.append(entry)
        if len(self.short_term) > SHORT_TERM_SIZE:
            # Konsolider til langtidsminne
            self._consolidate(self.short_term.pop(0))
        self._save_short_term()

        # 3. Oppdater semantisk indeks
        self._index_entry(entry)

        return uid

    def remember_fact(self, key: str, value: Any, category: str = "generelt") -> str:
        """Lagrer et faktum/kunnskap direkte i langtidsminnet."""
        content = f"[FAKT:{category}] {key} = {value}"
        uid = self.remember(content, meta={"type": "fakt", "key": key, "category": category})
        # Lagre strukturert
        facts_path = self.memory_dir / "semantisk" / "fakta.json"
        facts = json.loads(facts_path.read_text()) if facts_path.exists() else {}
        facts[key] = {"value": value, "category": category, "uid": uid,
                      "updated": datetime.datetime.now().isoformat()}
        facts_path.write_text(json.dumps(facts, ensure_ascii=False, indent=2))
        return uid

    def remember_episode(self, title: str, content: str) -> str:
        """Lagrer en episode (hendelse/samtale)."""
        ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.memory_dir / "episodisk" / f"{ts}_{title[:30]}.json"
        episode = {
            "title"    : title,
            "timestamp": ts,
            "content"  : content,
            "tags"     : self._extract_tags(content),
        }
        path.write_text(json.dumps(episode, ensure_ascii=False, indent=2))
        return self.remember(f"[EPISODE] {title}: {content[:200]}", meta={"type": "episode", "file": str(path)})

    # ---------- HENTING ----------

    def recall(self, query: str, n: int = 5) -> list:
        """Henter relevante minner basert på spørring - automatisk."""
        q_tags = set(self._extract_tags(query) + query.lower().split())
        scored = []
        for entry in list(self.long_term.values()) + self.short_term:
            entry_tags = set(entry.get("tags", []) + entry.get("content", "").lower().split())
            score = len(q_tags & entry_tags) + entry.get("importance", 0)
            if score > 0:
                scored.append((score, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:n]]

    def recall_fact(self, key: str) -> Optional[Any]:
        """Henter et lagret faktum."""
        facts_path = self.memory_dir / "semantisk" / "fakta.json"
        if not facts_path.exists():
            return None
        facts = json.loads(facts_path.read_text())
        return facts.get(key, {}).get("value")

    def get_context(self, query: str = None) -> str:
        """Bygger kontekst-streng for LLM - inkluderer relevante minner automatisk."""
        lines = ["=== AKTIV HUKOMMELSE ==="]
        # Korttidsminne
        lines.append("\n--- Korttidsminne (nylig) ---")
        for e in self.short_term[-5:]:
            lines.append(f"[{e['timestamp'][:16]}] {e['content'][:200]}")
        # Langtidsminne (relevant)
        if query:
            lines.append("\n--- Relevante langtidsminner ---")
            for e in self.recall(query, n=5):
                lines.append(f"[{e['timestamp'][:16]}] {e['content'][:200]}")
        # Fakta
        facts_path = self.memory_dir / "semantisk" / "fakta.json"
        if facts_path.exists():
            facts = json.loads(facts_path.read_text())
            if facts:
                lines.append("\n--- Kjente fakta ---")
                for k, v in list(facts.items())[-10:]:
                    lines.append(f"  {k} = {v['value']}")
        return "\n".join(lines)

    def get_short_context(self) -> list:
        """Returnerer korttidsminne som liste (for chat-historikk)."""
        return self.short_term[-SHORT_TERM_SIZE:]

    # ---------- KONSOLIDERING ----------

    def _consolidate(self, entry: dict):
        """Overforer fra korttid til langtid (som søvn gjor for mennesker)."""
        uid = entry["id"]
        self.long_term[uid] = entry
        self._save_long_term()

    def consolidate_all(self):
        """Tving konsolidering av alt korttidsminne."""
        while self.short_term:
            self._consolidate(self.short_term.pop(0))
        self._save_short_term()
        print("[Minne] All konsolidering fullfort.")

    # ---------- INDEKS ----------

    def _extract_tags(self, text: str) -> list:
        """Trekker ut nøkkelord automatisk."""
        words = re.findall(r'\b[a-zA-ZæøåÆØÅ]{3,}\b', text.lower())
        stopwords = {"den", "det", "deg", "jeg", "er", "for", "som", "med",
                     "til", "fra", "har", "kan", "vil", "ikke", "men", "the",
                     "and", "or", "that", "this", "with", "for", "are"}
        return list(set(w for w in words if w not in stopwords))[:20]

    def _score_importance(self, text: str) -> float:
        """Scorer viktighet automatisk."""
        score = 0.0
        high = ["viktig", "husk", "aldri", "alltid", "kritisk", "must", "important",
                "remember", "never", "always", "passord", "api", "nokkel", "key"]
        for word in high:
            if word in text.lower():
                score += 1.0
        score += min(len(text) / 500, 1.0)  # Lengde gir litt ekstra
        return round(score, 2)

    def _index_entry(self, entry: dict):
        idx_path = self.memory_dir / "semantisk" / "indeks.json"
        idx = json.loads(idx_path.read_text()) if idx_path.exists() else {}
        for tag in entry.get("tags", []):
            idx.setdefault(tag, []).append(entry["id"])
        idx_path.write_text(json.dumps(idx, ensure_ascii=False, indent=2))

    def _build_index(self) -> dict:
        idx_path = self.memory_dir / "semantisk" / "indeks.json"
        return json.loads(idx_path.read_text()) if idx_path.exists() else {}

    # ---------- PERSISTENS ----------

    def _load_short_term(self) -> list:
        p = self.memory_dir / "korttid" / "aktiv.json"
        return json.loads(p.read_text()) if p.exists() else []

    def _save_short_term(self):
        p = self.memory_dir / "korttid" / "aktiv.json"
        p.write_text(json.dumps(self.short_term, ensure_ascii=False, indent=2))

    def _load_long_term(self) -> dict:
        p = self.memory_dir / "langtid" / "hoved.json"
        return json.loads(p.read_text()) if p.exists() else {}

    def _save_long_term(self):
        p = self.memory_dir / "langtid" / "hoved.json"
        p.write_text(json.dumps(self.long_term, ensure_ascii=False, indent=2))

    # ---------- STATUS ----------

    def status(self) -> dict:
        return {
            "sensorisk"  : len(self.sensory),
            "korttid"    : len(self.short_term),
            "langtid"    : len(self.long_term),
            "indeks_tags": len(self.index),
        }

    def wipe_short_term(self):
        """Sletter korttidsminnet (som å glemme midlertidig)."""
        self.short_term = []
        self._save_short_term()
