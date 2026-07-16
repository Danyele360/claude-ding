"""Riproduce un MP3 personalizzato per gli hook di Claude Code (via MCI, zero dipendenze).

Copia questo file in C:\\Users\\<tuo-utente>\\.claude\\hooks\\stop_sound.py
e aggiorna SOUND_FILE con il percorso del tuo MP3.
"""

import ctypes

SOUND_FILE = r"C:\Users\<tuo-utente>\Music\ding.mp3"


def mci(command: str) -> None:
    ctypes.windll.winmm.mciSendStringW(command, None, 0, None)


mci(f'open "{SOUND_FILE}" type mpegvideo alias ding')
mci("play ding wait")
mci("close ding")
