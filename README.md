# 🔔 claude-ding

> Sound notifications for Claude Code on Windows — sappi quando Claude ha finito o ha bisogno di te, senza tenere d'occhio il terminale.

Fai suonare Claude Code quando **finisce di rispondere**, quando **ti fa una domanda** o quando **aspetta un permesso**.

## Come funziona

Claude Code supporta gli **hooks**: comandi shell eseguiti automaticamente in risposta a eventi del ciclo di vita della sessione. Qui ne usiamo tre:

| Evento | Quando scatta | Tempistica |
|---|---|---|
| `Stop` | Claude ha finito di rispondere | subito |
| `PreToolUse` (matcher `AskUserQuestion`) | Claude ti mostra una domanda a scelta multipla | subito |
| `PermissionRequest` | Appare il dialogo di permesso (Allow/Deny) | subito |
| `Notification` | Notifiche generiche o input fermo | subito / dopo 60s di inattività |

Tutti lanciano lo stesso script Python che riproduce un suono.

> 💡 Per i prompt di permesso usa `PermissionRequest`, non `Notification`: in alcuni ambienti (es. estensione VSCode) `Notification` non scatta in modo affidabile per i dialoghi Allow/Deny.

## Requisiti

- **Windows** (gli script usano API native di Windows)
- **Python** installato con il launcher `py` (verifica con `py --version`)
- Claude Code

## 1. Scegli e copia lo script audio

Copia uno dei due script di questa repo in `C:\Users\<tuo-utente>\.claude\hooks\stop_sound.py`:

### Opzione A — [`stop_sound.py`](stop_sound.py): suono di sistema di Windows (zero dipendenze)

```python
import winsound

winsound.MessageBeep(winsound.MB_ICONASTERISK)
```

Altri suoni disponibili: `MB_OK`, `MB_ICONQUESTION`, `MB_ICONEXCLAMATION`, `MB_ICONHAND`.

### Opzione B — [`stop_sound_mp3.py`](stop_sound_mp3.py): un tuo file MP3

`winsound` legge solo WAV, ma l'API multimediale di Windows (MCI, via `ctypes`) riproduce gli MP3 senza librerie esterne:

```python
import ctypes

SOUND_FILE = r"C:\Users\<tuo-utente>\Music\ding.mp3"


def mci(command: str) -> None:
    ctypes.windll.winmm.mciSendStringW(command, None, 0, None)


mci(f'open "{SOUND_FILE}" type mpegvideo alias ding')
mci("play ding wait")
mci("close ding")
```

Ricorda di aggiornare `SOUND_FILE` con il percorso del tuo MP3.

### Testa lo script

```powershell
py C:\Users\<tuo-utente>\.claude\hooks\stop_sound.py
```

Se senti il suono, sei a posto. ✅

## 2. Configura gli hooks

Apri (o crea) `C:\Users\<tuo-utente>\.claude\settings.json` e aggiungi la sezione `hooks` — trovi il blocco pronto in [`settings.example.json`](settings.example.json).

**Attenzione**: se il file esiste già, aggiungi solo la chiave `hooks` senza cancellare il resto.

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "py C:/Users/<tuo-utente>/.claude/hooks/stop_sound.py",
            "async": true,
            "timeout": 10
          }
        ]
      }
    ],
    "Notification": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "py C:/Users/<tuo-utente>/.claude/hooks/stop_sound.py",
            "async": true,
            "timeout": 10
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "AskUserQuestion",
        "hooks": [
          {
            "type": "command",
            "command": "py C:/Users/<tuo-utente>/.claude/hooks/stop_sound.py",
            "async": true,
            "timeout": 10
          }
        ]
      }
    ],
    "PermissionRequest": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "py C:/Users/<tuo-utente>/.claude/hooks/stop_sound.py",
            "async": true,
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

Note:

- `"async": true` → il suono parte in background senza rallentare Claude
- Percorsi con **slash normali** (`/`) o doppi backslash (`\\`) — mai backslash singoli nel JSON
- Configurandolo in `~/.claude/settings.json` vale per **tutti i progetti**; per un solo progetto usa `.claude/settings.local.json` nella root del repo

## 3. Ricarica la configurazione

Se hai una sessione Claude Code già aperta, apri una volta il menu `/hooks` (basta aprirlo e chiuderlo) oppure riavvia la sessione. Le nuove sessioni caricano gli hook automaticamente.

## Personalizzazioni

**Suoni diversi per eventi diversi** — crea due script (es. `done.py` e `question.py`) e assegnali a hook differenti: un suono per "ho finito", un altro per "mi serve una risposta".

**Suono WAV nativo** — con un `.wav` puoi restare su `winsound`:

```python
import winsound

winsound.PlaySound(r"C:\Windows\Media\tada.wav", winsound.SND_FILENAME)
```

**Volume** — MCI supporta anche `setaudio ding volume to 500` (scala 0–1000) prima del `play`.

## Risoluzione problemi

| Problema | Soluzione |
|---|---|
| Nessun suono, mai | Testa lo script a mano: `py ...\stop_sound.py`. Se suona, ricarica la config con `/hooks` o riavvia |
| `Python was not found` | Usa il launcher `py` invece di `python` (l'alias Microsoft Store spesso non funziona), oppure installa Python da [python.org](https://www.python.org/downloads/) |
| Il suono di "attesa input" arriva tardi | È normale: l'evento `Notification` per inattività scatta dopo 60 secondi (soglia fissa di Claude Code). Per le domande usa l'hook `PreToolUse` su `AskUserQuestion`, che è istantaneo |
| Nessun suono sui prompt Allow/Deny | Usa l'evento `PermissionRequest` invece di `Notification`: scatta esattamente quando appare il dialogo, in ogni ambiente |
| JSON rotto = hook spariti | Un `settings.json` malformato disattiva silenziosamente **tutte** le impostazioni del file. Valida il JSON dopo ogni modifica |

## Riferimenti

- [Documentazione ufficiale hooks di Claude Code](https://docs.claude.com/en/docs/claude-code/hooks)

## Licenza

MIT — fanne quello che vuoi. 🔔
