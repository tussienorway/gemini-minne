#!/usr/bin/env python3
"""
gemini_cli.py - Interaktiv CLI med fotografisk hukommelse
Kjør: python gemini_cli.py
Velg LLM-backend interaktivt eller via env-variabel LLM_BACKEND

Kommandoer:
  /bytt      - Bytt LLM-backend
  /husk X=Y  - Lagre et faktum manuelt
  /status    - Vis minnestatus
  /sync      - Synk minne til GitHub
  /recall X  - Søk i minnet
  /episode T - Lagre episode
  /toom      - Slett korttidsminnet
  /hjelp     - Vis hjelp
  /avslutt   - Avslutt og lagre session
"""

import os
import sys

# Farger for terminal
GROENN = "\033[92m"
GUL    = "\033[93m"
ROED   = "\033[91m"
BLAA   = "\033[94m"
CYAN   = "\033[96m"
FETT   = "\033[1m"
RESET  = "\033[0m"

BACKENDS = {
    "1": ("gemini",  "Google Gemini (standard)"),
    "2": ("openai",  "OpenAI GPT"),
    "3": ("ollama",  "Ollama (lokal, ingen API-nøkkel)"),
    "4": ("claude",  "Anthropic Claude"),
}


def velg_backend() -> str:
    """La brukeren velge LLM-backend."""
    print(f"\n{FETT}{CYAN}=== GEMINI-MINNE: Velg LLM-backend ==={RESET}")
    for k, (name, desc) in BACKENDS.items():
        print(f"  {GUL}{k}{RESET}. {GROENN}{name}{RESET} - {desc}")
    print(f"  {GUL}0{RESET}. Bruk {os.environ.get('LLM_BACKEND', 'gemini')} (fra .env)")
    valg = input(f"\n{BLAA}Velg [0-4]:{RESET} ").strip()
    if valg == "0" or valg not in BACKENDS:
        return os.environ.get("LLM_BACKEND", "gemini")
    backend, _ = BACKENDS[valg]
    return backend


def vis_banner(backend: str, status: dict):
    print(f"""
{FETT}{CYAN}╔{'==='*18}╗
║   GEMINI-MINNE - Fotografisk hukommelse for AI   ║
╚{'==='*18}╝{RESET}
{GROENN}Backend : {FETT}{backend.upper()}{RESET}
{GROENN}Minne   : {RESET}Korttid={status['korttid']} | Langtid={status['langtid']} | Indeks={status['indeks_tags']} tags
{GUL}Skriv /hjelp for kommandoer{RESET}
""")


def vis_hjelp():
    print(f"""
{FETT}{CYAN}--- KOMMANDOER ---{RESET}
{GUL}/bytt{RESET}          Bytt LLM-backend
{GUL}/husk X=Y{RESET}      Lagre faktum: /husk navn=Tussie
{GUL}/status{RESET}        Vis minnestatus
{GUL}/sync{RESET}          Sync minne til GitHub
{GUL}/recall X{RESET}      Søk i minne: /recall python
{GUL}/episode T{RESET}     Lagre episode med tittel T
{GUL}/toom{RESET}          Slett korttidsminnet
{GUL}/hjelp{RESET}         Vis denne hjelpen
{GUL}/avslutt{RESET}       Avslutt og lagre session
""")


def main():
    # Last miljøvariabler fra .env hvis tilgjengelig
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    # Velg backend
    backend = velg_backend()

    # Start agent
    try:
        from llm_agent import LLMAgent
        agent = LLMAgent(backend=backend)
    except Exception as e:
        print(f"{ROED}Feil ved oppstart: {e}{RESET}")
        sys.exit(1)

    # GitHub-sync ved oppstart
    github_sync = None
    try:
        from github_sync import GitHubSync
        github_sync = GitHubSync()
        if github_sync.is_configured():
            print(f"{GROENN}[GitHub] Kobler til...{RESET}")
            github_sync.restore_all()
        else:
            print(f"{GUL}[GitHub] Ikke konfigurert (sett GITHUB_TOKEN i .env){RESET}")
    except Exception as e:
        print(f"{GUL}[GitHub] Utilgjengelig: {e}{RESET}")

    vis_banner(backend, agent.memory_status())
    samtale_logg = []

    while True:
        try:
            user_input = input(f"{FETT}{BLAA}Du: {RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            user_input = "/avslutt"

        if not user_input:
            continue

        # --- KOMMANDOER ---
        if user_input.startswith("/bytt"):
            backend = velg_backend()
            try:
                agent = LLMAgent(backend=backend)
                print(f"{GROENN}Byttet til {backend}{RESET}")
            except Exception as e:
                print(f"{ROED}Feil: {e}{RESET}")
            continue

        elif user_input.startswith("/husk "):
            try:
                kv = user_input[6:].split("=", 1)
                if len(kv) == 2:
                    agent.remember(kv[0].strip(), kv[1].strip())
                    print(f"{GROENN}[Minne] Lagret: {kv[0].strip()} = {kv[1].strip()}{RESET}")
                else:
                    print(f"{GUL}Bruk: /husk nokkel=verdi{RESET}")
            except Exception as e:
                print(f"{ROED}Feil: {e}{RESET}")
            continue

        elif user_input == "/status":
            s = agent.memory_status()
            print(f"""
{CYAN}=== MINNESTATUS ==={RESET}
Sensorisk  : {s['sensorisk']}
Korttidsminne : {s['korttid']}
Langtidsminne : {s['langtid']}
Indeks-tags   : {s['indeks_tags']}
""")
            continue

        elif user_input == "/sync":
            if github_sync and github_sync.is_configured():
                print(f"{GUL}[GitHub] Synkroniserer...{RESET}")
                res = github_sync.sync_all()
                print(f"{GROENN}[GitHub] Ferdig: {len(res['ok'])} filer pushet{RESET}")
            else:
                print(f"{ROED}[GitHub] Ikke konfigurert. Sett GITHUB_TOKEN i .env{RESET}")
            continue

        elif user_input.startswith("/recall "):
            q = user_input[8:]
            minner = agent.recall(q)
            print(f"{CYAN}=== MINNER FOR '{q}' ==={RESET}")
            for m in minner:
                print(f"  [{m['timestamp'][:16]}] {m['content'][:150]}")
            if not minner:
                print("  (ingen minner funnet)")
            continue

        elif user_input.startswith("/episode "):
            tittel  = user_input[9:]
            innhold = input(f"{GUL}Beskriv episoden: {RESET}")
            uid = agent.save_episode(tittel, innhold)
            print(f"{GROENN}[Minne] Episode lagret: {tittel} (id: {uid}){RESET}")
            continue

        elif user_input == "/toom":
            agent.memory.wipe_short_term()
            print(f"{GUL}[Minne] Korttidsminnet slettet.{RESET}")
            continue

        elif user_input == "/hjelp":
            vis_hjelp()
            continue

        elif user_input in ("/avslutt", "/exit", "/quit"):
            print(f"{GUL}[Minne] Konsoliderer og lagrer session...{RESET}")
            agent.memory.consolidate_all()
            if github_sync and github_sync.is_configured():
                sammendrag = f"Session med {len(samtale_logg)} meldinger"
                github_sync.log_session(sammendrag)
                github_sync.sync_all()
                print(f"{GROENN}[GitHub] Session lagret til skyen.{RESET}")
            print(f"{CYAN}Ha det! Alle minner er lagret.{RESET}")
            break

        # --- VANLIG CHAT ---
        else:
            try:
                print(f"{GUL}[Tenker...]{RESET}")
                svar = agent.chat(user_input)
                samtale_logg.append({"bruker": user_input, "ai": svar})
                print(f"\n{FETT}{GROENN}AI: {RESET}{svar}\n")
            except Exception as e:
                print(f"{ROED}Feil: {e}{RESET}")


if __name__ == "__main__":
    main()
