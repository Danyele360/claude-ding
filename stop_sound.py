"""Riproduce il suono di notifica di Windows per gli hook di Claude Code.

Copia questo file in C:\\Users\\<tuo-utente>\\.claude\\hooks\\stop_sound.py
"""

import winsound

winsound.MessageBeep(winsound.MB_ICONASTERISK)
