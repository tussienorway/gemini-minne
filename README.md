# gemini-minne

> **Fotografisk hukommelse for AI** - Minnesystem som fungerer som menneskelig hjerne, med automatisk lagring og GitHub-skysync.

## Hva er dette?

`gemini-minne` er et fullstendig minnesystem for AI. Det fungerer som en ekte hjerne:

| Hjerne | gemini-minne |
|---|---|
| Sensorisk minne | RAM - siste 5 inntrykk |
| Korttidsminne | Aktiv samtale (20 meldinger) |
| Langtidsminne | Lokal JSON-database |
| Semantisk minne | Nokkelord-indeks og fakta |
| Episodisk minne | Lagrede hendelser/samtaler |
| Skysync | GitHub = hjernen din i skyen |

**Alt skjer automatisk** - ingen manuell jobb.

## Rask start

```bash
git clone https://github.com/tussienorway/gemini-minne.git
cd gemini-minne
pip install -r requirements.txt
cp .env.example .env
# Rediger .env og legg inn API-nokkel
python gemini_cli.py
```

## Velg LLM-backend

Nar du starter velger du:

```
1. gemini  - Google Gemini
2. openai  - OpenAI GPT
3. ollama  - Ollama (lokal, ingen API-nokkel)
4. claude  - Anthropic Claude
```

Eller via miljovariabel: `export LLM_BACKEND=ollama`

## CLI-kommandoer

| Kommando | Beskrivelse |
|---|---|
| `/bytt` | Bytt LLM-backend |
| `/husk navn=Tussie` | Lagre faktum |
| `/status` | Vis minnestatus |
| `/sync` | Sync til GitHub |
| `/recall python` | Sok i minnet |
| `/episode Tittel` | Lagre episode |
| `/toom` | Slett korttidsminnet |
| `/avslutt` | Avslutt og lagre |

## Filstruktur

```
gemini-minne/
  memory_core.py   # Hjernen - fotografisk hukommelse
  llm_agent.py     # LLM-agent med automatisk minne
  github_sync.py   # GitHub som langtidsminne
  gemini_cli.py    # Interaktiv CLI
  .env.example     # Mal for miljovariabler
  requirements.txt # Python-avhengigheter
  minne/           # Lokal minnebase (auto-opprettet)
```

## GitHub-token

1. Ga til https://github.com/settings/tokens
2. Generer klassisk token med `repo`-tilgang
3. Legg inn i `.env`: `GITHUB_TOKEN=ghp_ditt_token`

## Bruk i Python

```python
from llm_agent import LLMAgent

agent = LLMAgent(backend="gemini")  # gemini|openai|ollama|claude
svar = agent.chat("Hva er Python?")  # Minnet oppdateres automatisk
agent.remember("favoritt", "Python")  # Lagre faktum
minner = agent.recall("Python")        # Hent minner
print(agent.memory_status())           # Vis status
```

---
*Laget av tussienorway*
