"""Configura el chat de Telegram al que se envían los avisos.

Pasos (una sola vez):
  1. Pon el token del bot en .env:   TELEGRAM_BOT_TOKEN=123456:ABC...
  2. En Telegram, abre @datosextremadura_bot y envíale /start.
  3. Ejecuta telegram_configurar.bat.

El script comprueba el token, busca el chat desde el que se envió /start,
guarda TELEGRAM_CHAT_ID en .env y manda un mensaje de prueba. No muestra el
token en ningún momento. Salida: _ejecucion_claude/telegram_configurar.txt
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from extremadura_datos.config import Config  # noqa: E402,F401  (carga .env)

ENV = RAIZ / ".env"


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("ERROR: falta TELEGRAM_BOT_TOKEN en .env")
        return 1
    api = f"https://api.telegram.org/bot{token}"
    me = requests.get(f"{api}/getMe", timeout=30).json()
    if not me.get("ok"):
        print("ERROR: Telegram rechaza el token (¿revocado o mal copiado?).")
        return 1
    print(f"Bot correcto: @{me['result']['username']}")

    upd = requests.get(f"{api}/getUpdates", timeout=30).json()
    chats = []
    for u in upd.get("result", []):
        msg = u.get("message") or u.get("channel_post") or {}
        chat = msg.get("chat")
        if chat:
            chats.append((chat["id"], chat.get("type"), chat.get("first_name") or chat.get("title") or ""))
    if not chats:
        print("ERROR: el bot no ha recibido mensajes. Envíale /start desde Telegram y vuelve a ejecutar.")
        return 1
    chat_id, tipo, nombre = chats[-1]
    print(f"Chat encontrado: {tipo} «{nombre}» (id {chat_id})")

    texto = ENV.read_text(encoding="utf-8")
    if re.search(r"^TELEGRAM_CHAT_ID=.*$", texto, flags=re.M):
        texto = re.sub(r"^TELEGRAM_CHAT_ID=.*$", f"TELEGRAM_CHAT_ID={chat_id}", texto, flags=re.M)
    else:
        texto = texto.rstrip("\n") + f"\nTELEGRAM_CHAT_ID={chat_id}\n"
    ENV.write_text(texto, encoding="utf-8")
    print("TELEGRAM_CHAT_ID guardado en .env")

    r = requests.post(f"{api}/sendMessage", json={
        "chat_id": chat_id, "parse_mode": "HTML",
        "text": "✅ <b>Extremadura en Datos</b>\nEste chat recibirá los avisos de datos nuevos después de la carga diaria de las 8:00.",
    }, timeout=30)
    print("Mensaje de prueba:", "enviado" if r.status_code == 200 else f"error {r.status_code}")
    return 0 if r.status_code == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
