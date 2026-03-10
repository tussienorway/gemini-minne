#!/usr/bin/env python3
"""
memory_core.py v2 - Avansert kognitiv arkitektur for AI
Inkluderer: Vektorsøk-emulering, Memory Decay, Importance Scoring, og Kontekst-komprimering.
"""
import json
import os
import re
import hashlib
import datetime
import math
from pathlib import Path
from typing import Any, Optional, List, Dict

MEMORY_DIR = Path(os.environ.get("MEMORY_DIR", "./minne"))
SHORT_TERM_SIZE = int(os.environ.get("SHORT_TERM_SIZE", "20"))
DECAY_FACTOR = float(os.environ.get("MEMORY_DECAY", "0.99")) # Minner mister verdi over tid

class MemoryCore:
    def __init__(self):
        self.memory_dir = MEMORY_DIR
        self._setup_dirs()
        self.sensory = []
        self.short_term = self._load_json("korttid/aktiv.json", [])
        self.long_term = self._load_json("langtid/hoved.json", {})
        self.facts = self._load_json("semantisk/fakta.json", {})
        self.index = self._load_json("semantisk/indeks.json", {})

    def _setup_dirs(self):
        for sub in ["korttid", "langtid", "episodisk", "semantisk", "prosedyre", "arkiv"]:
            (self.memory_dir / sub).mkdir(parents=True, exist_ok=True)

    def _load_json(self, path: str, default: Any) -> Any:
        p = self.memory_dir / path
        if p.exists():
            try: return json.loads(p.read_text(encoding="utf-8"))
            except: return default
        return default

    def _save_json(self, path: str, data: Any):
        p = self.memory_dir / path
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def remember(self, content: str, meta: dict = None) -> str:
        ts = datetime.datetime.now().isoformat()
        uid = hashlib.md5((content + ts).encode()).hexdigest()[:12]
        
        entry = {
            "id": uid,
            "timestamp": ts,
            "content": content,
            "meta": meta or {},
            "tags": self._extract_tags(content),
            "importance": self._score_importance(content),
            "access_count": 1,
            "last_accessed": ts
        }

        # Sensorisk (flyktig)
        self.sensory.append(entry)
        if len(self.sensory) > 10: self.sensory.pop(0)

        # Korttid
        self.short_term.append(entry)
        self._save_json("korttid/aktiv.json", self.short_term)

        # Auto-konsolidering hvis full
        if len(self.short_term) > SHORT_TERM_SIZE:
            self._consolidate(self.short_term.pop(0))

        self._index_entry(entry)
        return uid

    def _score_importance(self, text: str) -> float:
        score = 1.0
        triggers = {
            "viktig": 2.0, "husk": 2.0, "aldri": 1.5, "alltid": 1.5,
            "passord": 5.0, "api": 4.0, "key": 4.0, "bruker": 1.2
        }
        for word, weight in triggers.items():
            if word in text.lower(): score += weight
        
        # Lengde-bias (opp til 2.0 ekstra)
        score += min(len(text) / 1000, 2.0)
        return round(score, 2)

    def _extract_tags(self, text: str) -> List[str]:
        words = re.findall(r'\b[a-zA-ZæøåÆØÅ]{4,}\b', text.lower())
        stopwords = {"dette", "eller", "fordi", "skal", "ville", "når", "hvis"}
        return list(set(w for w in words if w not in stopwords))[:15]

    def _consolidate(self, entry: dict):
        # Flytt til langtid med betydnings-sjekk
        if entry["importance"] > 1.5 or entry["access_count"] > 1:
            self.long_term[entry["id"]] = entry
            self._save_json("langtid/hoved.json", self.long_term)
        else:
            # Arkiver uviktige minner i stedet for å slette
            self._archive(entry)

    def _archive(self, entry: dict):
        date_str = entry["timestamp"][:10]
        arch_path = f"arkiv/{date_str}.json"
        arch = self._load_json(arch_path, [])
        arch.append(entry)
        self._save_json(arch_path, arch)

    def recall(self, query: str, limit: int = 7) -> List[dict]:
        q_tags = set(self._extract_tags(query) + query.lower().split())
        scored = []
        now = datetime.datetime.now()

        # Søk i både korttid og langtid
        candidates = self.short_term + list(self.long_term.values())
        
        for entry in candidates:
            # 1. Semantisk likhet (tag overlap)
            e_tags = set(entry.get("tags", []) + entry.get("content", "").lower().split())
            tag_score = len(q_tags & e_tags) * 2.0
            
            # 2. Memory Decay (nyere minner er sterkere)
            entry_time = datetime.datetime.fromisoformat(entry["timestamp"])
            days_old = (now - entry_time).days
            decay = math.pow(DECAY_FACTOR, days_old)
            
            # 3. Base importance + access frequency
            importance = entry.get("importance", 1.0)
            recency_bonus = 2.0 if days_old < 1 else 0.0
            
            final_score = (tag_score + importance) * decay + recency_bonus
            
            if final_score > 0.5:
                scored.append((final_score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = [e for _, e in scored[:limit]]
        
        # Oppdater tilgangsstatistikk
        for e in results:
            e["access_count"] = e.get("access_count", 0) + 1
            e["last_accessed"] = now.isoformat()
            
        return results

    def get_context(self, query: str = None) -> str:
        lines = ["### KOGNITIV KONTEKST ###"]
        
        # 1. Relevante fakta (Høyeste prioritet)
        if query:
            relevant_facts = [f"{k}: {v['value']}" for k, v in self.facts.items() if any(t in k.lower() or t in str(v['value']).lower() for t in query.lower().split())]
            if relevant_facts:
                lines.append("
[FAKTA]")
                lines.extend(relevant_facts[:5])

        # 2. Relevante minner via Recall
        if query:
            memories = self.recall(query)
            if memories:
                lines.append("
[RELEVANTE MINNER]")
                for m in memories:
                    lines.append(f"- ({m['timestamp'][:10]}) {m['content'][:300]}")

        # 3. Siste korttid (nylig historikk)
        lines.append("
[NYLIG HISTORIKK]")
        for m in self.short_term[-5:]:
            lines.append(f"- {m['content'][:200]}")

        return "
".join(lines)

    def _index_entry(self, entry: dict):
        for tag in entry.get("tags", []):
            if tag not in self.index: self.index[tag] = []
            if entry["id"] not in self.index[tag]:
                self.index[tag].append(entry["id"])
        self._save_json("semantisk/indeks.json", self.index)

    def status(self) -> dict:
        return {
            "sensory_buffer": len(self.sensory),
            "short_term_active": len(self.short_term),
            "long_term_total": len(self.long_term),
            "semantic_tags": len(self.index),
            "facts_known": len(self.facts)
        }
