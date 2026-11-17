import os
import time
import requests
import re
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "9219638473:AAEYp5u89YbG2TjuyKeXrCJJIHvlSwqCLJo")

def detect_and_save_chat_id():
    print("=" * 60)
    print("   AUTODETECTOR DE TELEGRAM CHAT ID")
    print("=" * 60)
    print("1. Abre Telegram en tu móvil o PC.")
    print("2. Entra en el chat de tu bot: https://t.me/frankybet365bot")
    print("3. Pulsa 'INICIAR' (Start) o envíale un mensaje cualquiera (ej. 'hola').")
    print("Esperando tu mensaje en Telegram (presiona Ctrl+C para cancelar)...")
    print("-" * 60)

    url_updates = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    
    start_time = time.time()
    while True:
        try:
            resp = requests.get(url_updates, timeout=10)
            data = resp.json()
            if data.get("ok"):
                results = data.get("result", [])
                if results:
                    last_update = results[-1]
                    msg = last_update.get("message") or last_update.get("channel_post")
                    if msg and "from" in msg:
                        user_info = msg["from"]
                        chat_id = user_info.get("id")
                        first_name = user_info.get("first_name", "")
                        username = user_info.get("username", "")

                        print(f"\n🎉 ¡MENSAJE DETECTADO!")
                        print(f"👤 Usuario: {first_name} (@{username})")
                        print(f"🆔 Tu Chat ID numérico es: {chat_id}")

                        # Actualizar archivo .env
                        env_path = os.path.join(os.path.dirname(__file__), ".env")
                        if os.path.exists(env_path):
                            with open(env_path, "r", encoding="utf-8") as f:
                                content = f.read()

                            if "TELEGRAM_CHAT_ID=" in content:
                                new_content = re.sub(r"TELEGRAM_CHAT_ID=.*", f"TELEGRAM_CHAT_ID={chat_id}", content)
                            else:
                                new_content = content + f"\nTELEGRAM_CHAT_ID={chat_id}\n"

                            with open(env_path, "w", encoding="utf-8") as f:
                                f.write(new_content)
                            print("✅ Archivo .env actualizado correctamente con tu TELEGRAM_CHAT_ID.")

                        # Enviar mensaje de prueba al usuario
                        send_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
                        test_text = (
                            f"👋 ¡Hola {first_name}!\n\n"
                            f"🤖 <b>Bot de Apuestas (+EV) conectado con éxito.</b>\n"
                            f"A partir de mañana a las 12:00 PM recibirás aquí los mejores picks con valor detectados."
                        )
                        requests.post(send_url, json={"chat_id": chat_id, "text": test_text, "parse_mode": "HTML"})
                        print("🚀 ¡Mensaje de confirmación enviado a tu Telegram!")
                        return chat_id
            
        except Exception as e:
            print(f"Error consultando Telegram: {e}")

        time.sleep(2)
        if time.time() - start_time > 120:
            print("\nTiempo de espera agotado (2 minutos). Vuelve a ejecutar este script cuando le hayas enviado un mensaje al bot.")
            break

if __name__ == "__main__":
    detect_and_save_chat_id()
