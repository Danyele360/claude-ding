# 🔔 claude-ding

> Notifiche sonore e tattili per Claude Code — sappi quando Claude ha finito o ha bisogno di te, senza tenere d'occhio il terminale.

Fai avvisare Claude Code quando **finisce di rispondere**, quando **ti fa una domanda** o quando **aspetta un permesso**.

Due scenari, due percorsi:

| Il tuo setup | Vai a |
|---|---|
| Claude Code sul tuo PC **Windows** | [Percorso A — Windows](#percorso-a--windows) |
| Claude Code su una macchina **Linux** a cui ti colleghi in **SSH** (anche da Android: Terminus, Termux, JuiceSSH…) | [Percorso B — Linux via SSH](#percorso-b--linux-via-ssh) |

## Come funziona

Claude Code supporta gli **hooks**: comandi shell eseguiti automaticamente in risposta a eventi del ciclo di vita della sessione. Qui ne usiamo quattro:

| Evento | Quando scatta | Tempistica |
|---|---|---|
| `Stop` | Claude ha finito di rispondere | subito |
| `PreToolUse` (matcher `AskUserQuestion`) | Claude ti mostra una domanda a scelta multipla | subito |
| `PermissionRequest` | Appare il dialogo di permesso (Allow/Deny) | subito |
| `Notification` | Notifiche generiche o input fermo | subito / dopo 60s di inattività |

Tutti lanciano lo stesso script, che avvisa te.

> 💡 Per i prompt di permesso usa `PermissionRequest`, non `Notification`: in alcuni ambienti (es. estensione VSCode) `Notification` non scatta in modo affidabile per i dialoghi Allow/Deny.

---

# Percorso A — Windows

Claude Code gira sul tuo PC e il suono esce dalle tue casse.

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
    ]
  }
}
```

Il file di esempio contiene tutti e quattro gli eventi.

Note:

- `"async": true` → il suono parte in background senza rallentare Claude
- Percorsi con **slash normali** (`/`) o doppi backslash (`\\`) — mai backslash singoli nel JSON
- Configurandolo in `~/.claude/settings.json` vale per **tutti i progetti**; per un solo progetto usa `.claude/settings.local.json` nella root del repo

---

# Percorso B — Linux via SSH

Claude Code gira su un server (VPS, LXC, Raspberry, WSL) e tu lo guardi da un client SSH — magari dal telefono. Qui il problema è un altro: **un mp3 riprodotto sul server non lo sente nessuno**. La notifica deve viaggiare fino a te.

[`claude_ding.py`](claude_ding.py) usa due canali indipendenti, entrambi opzionali:

| Canale | Cosa fa | Serve altro? |
|---|---|---|
| **BEL** | Scrive una raffica di caratteri `\a` sul terminale della tua sessione. Il client SSH la traduce in una **vibrazione continua** di circa un secondo | No: zero dipendenze, zero rete |
| **ntfy** | Manda una **push** al telefono, con il suono di notifica che scegli tu | App [ntfy](https://ntfy.sh) e connessione |

Se ntfy non è configurato resta solo il BEL. Se non c'è un terminale (cron, sessione non interattiva) resta solo ntfy.

## Requisiti

- **Linux** con `python3` (solo libreria standard, niente `pip install`)
- Claude Code
- Un client SSH che vibri o suoni sul BEL — su Android **Terminus** vibra di default

## 1. Installa lo script

```bash
mkdir -p ~/.claude/hooks
curl -o ~/.claude/hooks/claude_ding.py \
  https://raw.githubusercontent.com/Danyele360/claude-ding/main/claude_ding.py
chmod +x ~/.claude/hooks/claude_ding.py
```

Provalo subito, in primo piano così vedi eventuali errori:

```bash
python3 ~/.claude/hooks/claude_ding.py stop --fg
```

Il telefono deve vibrare per circa un secondo. ✅

> Lo script trova da solo il terminale giusto risalendo l'albero dei processi fino alla sessione `claude`. Con più sessioni SSH aperte, ognuna fa vibrare soltanto se stessa. Se il rilevamento fallisce puoi forzarlo: `CLAUDE_DING_TTY=/dev/pts/3`.

## 2. (Opzionale) Attiva la push con il tuo suono

Il BEL ti dà la vibrazione, ma il suono è quello del client SSH. Per sentire **il tuo mp3** serve ntfy.

1. Installa l'app **ntfy** ([Play Store](https://play.google.com/store/apps/details?id=io.heckel.ntfy) o [F-Droid](https://f-droid.org/packages/io.heckel.ntfy/))
2. Genera un topic lungo e imprevedibile — chiunque lo indovini riceve le tue notifiche:

   ```bash
   python3 -c "import secrets; print('claude-ding-' + secrets.token_urlsafe(12))"
   ```

3. Scrivi la configurazione in `~/.claude/hooks/claude-ding.json`:

   ```json
   {
     "ntfy_server": "https://ntfy.sh",
     "ntfy_topic": "claude-ding-IL-TUO-TOPIC",
     "bell_duration": 1.0,
     "bell_interval": 0.05
   }
   ```

   ```bash
   chmod 600 ~/.claude/hooks/claude-ding.json
   ```

4. Nell'app ntfy iscriviti allo stesso topic
5. Metti il tuo mp3 nella cartella `Notifications/` della memoria interna del telefono, poi nell'app ntfy: impostazioni della sottoscrizione → **suono personalizzato** → scegli il tuo file

Ogni chiave è sovrascrivibile da variabile d'ambiente: `CLAUDE_DING_NTFY_TOPIC`, `CLAUDE_DING_NTFY_SERVER`, `CLAUDE_DING_BELL_DURATION`, `CLAUDE_DING_BELL_INTERVAL`.

Le notifiche cambiano in base all'evento, così capisci perché Claude ti chiama senza aprire il telefono:

| Hook | Notifica |
|---|---|
| `Stop` | ✅ Claude ha finito |
| `AskUserQuestion` | ❓ Claude ti fa una domanda |
| `PermissionRequest` | 🔐 Claude chiede un permesso |
| `Notification` | 🔔 Claude ti sta aspettando |

## 3. Configura gli hooks

Aggiungi la chiave `hooks` a `~/.claude/settings.json` — blocco pronto in [`settings.linux.example.json`](settings.linux.example.json):

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/claude_ding.py stop",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

**Attenzione**: se il file esiste già, aggiungi solo la chiave `hooks` senza cancellare il resto.

Non serve mandare il comando in background con `&`: lo script si stacca da solo dopo aver individuato il terminale e l'hook restituisce il controllo in una frazione di secondo. Anzi, `setsid` o `&` nel comando **romperebbero** il rilevamento del terminale, perché il processo verrebbe riassegnato a init prima di poter risalire l'albero.

---

## Ricarica la configurazione

Se hai una sessione Claude Code già aperta, apri una volta il menu `/hooks` (basta aprirlo e chiuderlo) oppure riavvia la sessione. Le nuove sessioni caricano gli hook automaticamente.

## Personalizzazioni

**Suoni diversi per eventi diversi** — su Windows crea due script (es. `done.py` e `question.py`) e assegnali a hook differenti. Su Linux l'evento arriva già come argomento: basta differenziare il comportamento nel dizionario `EVENTS`.

**Vibrazione più lunga o più corta** — cambia `bell_duration` (secondi). `bell_interval` regola quanto sono fitti i BEL: intorno ai 50 ms le vibrazioni si fondono in una sola, molto più in là si sentono a scatti.

**Suono WAV nativo su Windows** — con un `.wav` puoi restare su `winsound`:

```python
import winsound

winsound.PlaySound(r"C:\Windows\Media\tada.wav", winsound.SND_FILENAME)
```

**Volume su Windows** — MCI supporta `setaudio ding volume to 500` (scala 0–1000) prima del `play`.

**ntfy self-hosted** — se non vuoi passare da un server pubblico, punta `ntfy_server` alla tua istanza.

## Risoluzione problemi

| Problema | Soluzione |
|---|---|
| **Windows**: nessun suono, mai | Testa lo script a mano: `py ...\stop_sound.py`. Se suona, ricarica la config con `/hooks` o riavvia |
| **Windows**: `Python was not found` | Usa il launcher `py` invece di `python` (l'alias Microsoft Store spesso non funziona), oppure installa Python da [python.org](https://www.python.org/downloads/) |
| **Linux**: nessuna vibrazione | Lancia `python3 ~/.claude/hooks/claude_ding.py stop --fg`: in primo piano vedi l'errore. Controlla poi che il tuo client SSH abbia il bell attivo |
| **Linux**: vibra a scatti invece che di continuo | Abbassa `bell_interval` (prova `0.03`) |
| **Linux**: la push non arriva | Verifica il topic: `curl -s "https://ntfy.sh/IL-TUO-TOPIC/json?poll=1"` deve mostrare i messaggi inviati |
| L'avviso di "attesa input" arriva tardi | È normale: l'evento `Notification` per inattività scatta dopo 60 secondi (soglia fissa di Claude Code). Per le domande usa l'hook `PreToolUse` su `AskUserQuestion`, che è istantaneo |
| Nessun avviso sui prompt Allow/Deny | Usa l'evento `PermissionRequest` invece di `Notification`: scatta esattamente quando appare il dialogo, in ogni ambiente |
| JSON rotto = hook spariti | Un `settings.json` malformato disattiva silenziosamente **tutte** le impostazioni del file. Valida il JSON dopo ogni modifica |

## Riferimenti

- [Documentazione ufficiale hooks di Claude Code](https://docs.claude.com/en/docs/claude-code/hooks)
- [ntfy — notifiche push via HTTP](https://ntfy.sh)

## Licenza

MIT — fanne quello che vuoi. 🔔
