#!/usr/bin/env python3
"""
llm_agent.py - Valgfri LLM-backend med automatisk minne
Støtter: Gemini, OpenAI (GPT), Ollama (lokal), Anthropic (Claude)
Minnet injiseres automatisk i alle samtaler.
"""

import os
from typing import Optional
from memory_core import MemoryCore

LLM_BACKEND = os.environ.get("LLM_BACKEND", "gemini")  # gemini | openai | ollama | claude


class LLMAgent:
    """
    Universell LLM-agent med fotografisk hukommelse.
    Velg backend via LLM_BACKEND environment-variabel.
    Minnet er alltid aktivt - ingen manuell jobb.
    """

    def __init__(self, backend: str = None):
        self.backend = (backend or LLM_BACKEND).lower()
        self.memory  = MemoryCore()
        self.client  = self._init_client()
        print(f"[Agent] Starter med {self.backend}-backend + fotografisk hukommelse")
        print(f"[Agent] Minnestatus: {self.memory.status()}")

    def _init_client(self):
        """Initialiserer valgt LLM-klient."""
        if self.backend == "gemini":
            return self._init_gemini()
        elif self.backend == "openai":
            return self._init_openai()
        elif self.backend == "ollama":
            return self._init_ollama()
        elif self.backend == "claude":
            return self._init_claude()
        else:
            raise ValueError(f"Ukjent backend: {self.backend}. Velg: gemini, openai, ollama, claude")

    def _init_gemini(self):
        try:
            import google.generativeai as genai
            api_key = os.environ.get("GEMINI_API_KEY", "")
            genai.configure(api_key=api_key)
            model_name = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
            return genai.GenerativeModel(
                model_name=model_name,
                system_instruction=self._system_prompt()
            )
        except ImportError:
            raise ImportError("Kjør: pip install google-generativeai")

    def _init_openai(self):
        try:
            from openai import OpenAI
            return OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
        except ImportError:
            raise ImportError("Kjør: pip install openai")

    def _init_ollama(self):
        try:
            import ollama
            return ollama
        except ImportError:
            raise ImportError("Kjør: pip install ollama  (og ha Ollama kjørende lokalt)")

    def _init_claude(self):
        try:
            import anthropic
            return anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        except ImportError:
            raise ImportError("Kjør: pip install anthropic")

    def _system_prompt(self) -> str:
        """Systemprompt som alltid inkluderer minne-kontekst."""
        return """Du er en intelligent AI-assistent med fotografisk hukommelse.
Du husker ALT som har blitt fortalt deg - fra første samtale til nå.
Du har tilgang til:
- Korttidsminne: nylige samtaler
- Langtidsminne: alt som er blitt lagret
- Fakta-database: kjente fakta om brukeren og verden
- Episodisk minne: tidligere samtaler og hendelser

Bruk alltid hukommelsen aktivt. Referer til tidligere samtaler når det er relevant.
Oppfr deg som en person som husker alt perfekt."""

    # ---------- CHAT ----------

    def chat(self, user_input: str) -> str:
        """
        Send melding - minnet oppdateres automatisk før og etter.
        Du trenger ikke gjøre noe annet.
        """
        # 1. Lagre brukerens melding automatisk
        self.memory.remember(f"[Bruker] {user_input}")

        # 2. Hent relevant kontekst fra minnet
        context = self.memory.get_context(user_input)

        # 3. Send til LLM med kontekst
        response = self._send(user_input, context)

        # 4. Lagre svaret automatisk
        self.memory.remember(f"[AI] {response}")

        # 5. Sjekk om bruker oppgir fakta (automatisk gjenkjenning)
        self._auto_extract_facts(user_input)

        return response

    def _send(self, user_input: str, context: str) -> str:
        """Sender til valgt LLM med minnekontekst."""
        full_prompt = f"{context}\n\n[Ny melding fra bruker]\n{user_input}"

        if self.backend == "gemini":
            response = self.client.generate_content(full_prompt)
            return response.text

        elif self.backend == "openai":
            model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
            r = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": self._system_prompt()},
                    {"role": "user",   "content": full_prompt}
                ]
            )
            return r.choices[0].message.content

        elif self.backend == "ollama":
            model = os.environ.get("OLLAMA_MODEL", "llama3")
            r = self.client.chat(model=model, messages=[
                {"role": "system", "content": self._system_prompt()},
                {"role": "user",   "content": full_prompt}
            ])
            return r["message"]["content"]

        elif self.backend == "claude":
            model = os.environ.get("CLAUDE_MODEL", "claude-3-5-haiku-20241022")
            r = self.client.messages.create(
                model=model,
                max_tokens=4096,
                system=self._system_prompt(),
                messages=[{"role": "user", "content": full_prompt}]
            )
            return r.content[0].text

        return "[Feil: ingen backend svarte]"

    def _auto_extract_facts(self, text: str):
        """
        Automatisk gjenkjenning av fakta i teksten.
        Lagrer fakta uten at brukeren trenger å si det eksplisitt.
        """
        import re
        # Gjenkjenn mønstre som "jeg heter X", "jeg bor i X", "mitt passord er X" etc.
        patterns = [
            (r"jeg heter ([\w\s]+)",              "navn"),
            (r"jeg bor i ([\w\s,]+)",              "sted"),
            (r"jeg jobber (med|som|i) ([\w\s]+)",  "jobb"),
            (r"jeg er ([\d]+) år",                 "alder"),
            (r"api[- ]?key[:\s]+([\w\-]+)",         "api_key"),
            (r"min e-?post er ([\w@\.]+)",          "epost"),
        ]
        for pattern, key in patterns:
            m = re.search(pattern, text.lower())
            if m:
                value = m.group(m.lastindex or 1).strip()
                self.memory.remember_fact(key, value, category="bruker")
                print(f"[Minne] Auto-lagret fakt: {key} = {value}")

    # ---------- HJELP ----------

    def remember(self, key: str, value) -> str:
        """Lagrer et faktum eksplisitt."""
        return self.memory.remember_fact(key, value)

    def recall(self, query: str) -> list:
        """Henter minner relatert til en spørring."""
        return self.memory.recall(query)

    def memory_status(self) -> dict:
        """Viser minnestatus."""
        return self.memory.status()

    def save_episode(self, title: str, content: str) -> str:
        """Lagrer en viktig hendelse."""
        return self.memory.remember_episode(title, content)

    def get_backends() -> list:
        """Viser tilgjengelige backends."""
        return ["gemini", "openai", "ollama", "claude"]
