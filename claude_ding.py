#!/usr/bin/env python3
"""claude-ding — notifiche tattili e sonore per Claude Code su Linux via SSH.

Pensato per chi lavora da un client SSH mobile (es. Terminus su Android):
Claude gira sul server, ma la notifica deve arrivare in mano a te.

Fa due cose, indipendenti e opzionali:

  1. BEL — scrive una raffica di caratteri \\a sul terminale della sessione.
     Il client SSH la traduce in una vibrazione continua. Zero dipendenze,
     zero rete, latenza nulla.

  2. ntfy — manda una push HTTP a ntfy.sh (o a un ntfy self-hosted), così sul
     telefono senti il suono di notifica che hai scelto tu.

Se ntfy non è configurato resta solo il BEL. Se non c'è un terminale (cron,
sessione non interattiva) resta solo ntfy. Nessuno dei due è obbligatorio.

Uso:
    claude_ding.py <evento> [--fg]

    evento = stop | question | permission | notification
    --fg   = resta in primo piano invece di staccarsi (per i test: mostra
             gli errori e attende la fine della vibrazione)

Di default lo script si stacca in background dopo aver individuato il
terminale, così l'hook restituisce subito il controllo e il secondo di
vibrazione non rallenta la sessione. L'ordine conta: il terminale va
cercato PRIMA di staccarsi, perché dopo il fork il processo viene
riassegnato a init e l'albero dei processi non porta più al pts.

Lo script non fallisce mai in modo rumoroso: qualunque errore viene scritto
su stderr e il processo esce comunque con codice 0. Un hook rotto non deve
disturbare la sessione.
"""

import json
import os
import sys
import time
import urllib.request

CONFIG_PATH = os.path.expanduser("~/.claude/hooks/claude-ding.json")

DEFAULTS = {
    "ntfy_server": "https://ntfy.sh",
    "ntfy_topic": "",
    "bell_duration": 1.0,
    "bell_interval": 0.05,
}

# Titolo, corpo, tag ntfy e priorità per ciascun evento.
# I titoli restano ASCII: gli header HTTP di ntfy non digeriscono le emoji,
# che passano invece dai tag.
EVENTS = {
    "stop": ("Claude ha finito", "La risposta e' pronta.", "white_check_mark", 3),
    "question": ("Claude ti fa una domanda", "Aspetta che tu scelga.", "question", 4),
    "permission": ("Claude chiede un permesso", "Allow o Deny?", "lock", 4),
    "notification": ("Claude ti sta aspettando", "Input fermo.", "bell", 3),
}


def load_config():
    """Config da file, sovrascrivibile dalle variabili d'ambiente CLAUDE_DING_*."""
    config = dict(DEFAULTS)

    try:
        with open(CONFIG_PATH, encoding="utf-8") as handle:
            config.update(json.load(handle))
    except FileNotFoundError:
        pass

    for key in DEFAULTS:
        value = os.environ.get("CLAUDE_DING_" + key.upper())
        if value:
            config[key] = value

    for key in ("bell_duration", "bell_interval"):
        try:
            config[key] = float(config[key])
        except (TypeError, ValueError):
            config[key] = DEFAULTS[key]

    return config


def find_terminal():
    """Il /dev/pts della sessione, risalendo l'albero dei processi.

    Gli hook vengono lanciati con stdin/stdout rediretti, quindi il terminale
    non è nostro: appartiene a un antenato (il processo `claude`). Risaliamo
    la catena dei ppid finché uno dei descrittori standard non punta a un pts.
    """
    forced = os.environ.get("CLAUDE_DING_TTY")
    if forced:
        return forced

    pid = os.getpid()
    for _ in range(20):
        for fd in (0, 1, 2):
            try:
                target = os.readlink(f"/proc/{pid}/fd/{fd}")
            except OSError:
                continue
            if target.startswith("/dev/pts/"):
                return target

        try:
            with open(f"/proc/{pid}/stat", encoding="utf-8") as handle:
                stat = handle.read()
        except OSError:
            return None

        # Il nome del comando sta fra parentesi e può contenere spazi:
        # si parte a leggere i campi dopo l'ultima ')'.
        try:
            pid = int(stat[stat.rindex(")") + 1:].split()[1])
        except (ValueError, IndexError):
            return None

        if pid <= 1:
            return None

    return None


def buzz(config, terminal):
    """Raffica di BEL: tanti \\a ravvicinati fondono in una vibrazione unica."""
    if not terminal:
        return False

    deadline = time.monotonic() + config["bell_duration"]
    with open(terminal, "wb", buffering=0) as tty:
        while True:
            tty.write(b"\a")
            if time.monotonic() >= deadline:
                return True
            time.sleep(config["bell_interval"])


def push(config, event):
    """Notifica ntfy. Silenziosamente saltata se manca il topic."""
    topic = str(config["ntfy_topic"]).strip()
    if not topic:
        return False

    title, message, tags, priority = EVENTS[event]
    request = urllib.request.Request(
        f"{str(config['ntfy_server']).rstrip('/')}/{topic}",
        data=message.encode("utf-8"),
        headers={
            "Title": title,
            "Tags": tags,
            "Priority": str(priority),
        },
        method="POST",
    )
    urllib.request.urlopen(request, timeout=5).close()
    return True


def detach():
    """Fork in background e chiusura degli stdio ereditati dall'hook.

    Chiudere stdin/stdout/stderr non è un dettaglio: se il figlio tenesse
    aperte le pipe dell'hook, Claude Code resterebbe in attesa della loro
    chiusura e il lavoro in background sarebbe inutile.
    """
    if os.fork() > 0:
        os._exit(0)

    os.setsid()
    null = os.open(os.devnull, os.O_RDWR)
    for fd in (0, 1, 2):
        os.dup2(null, fd)
    if null > 2:
        os.close(null)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    foreground = "--fg" in sys.argv

    event = args[0].lower() if args else "stop"
    if event not in EVENTS:
        print(f"claude-ding: evento sconosciuto '{event}'", file=sys.stderr)
        event = "stop"

    config = load_config()

    # Prima il terminale, poi il distacco: dopo il fork l'albero dei processi
    # non risale più fino alla sessione Claude.
    terminal = find_terminal()

    if not foreground:
        try:
            detach()
        except OSError as error:
            print(f"claude-ding: fork fallito: {error}", file=sys.stderr)

    # I due canali sono indipendenti: se uno esplode, l'altro deve partire.
    for name, action in (("bell", lambda: buzz(config, terminal)),
                         ("ntfy", lambda: push(config, event))):
        try:
            action()
        except Exception as error:  # noqa: BLE001 - un hook non deve mai propagare
            print(f"claude-ding: {name} fallito: {error}", file=sys.stderr)


if __name__ == "__main__":
    main()
    sys.exit(0)
