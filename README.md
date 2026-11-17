# ⚽ Bot de Apuestas con Valor Esperado (+EV)

Sistema autónomo desarrollado en Python para escanear partidos de fútbol diarios, calcular la probabilidad real del mercado mediante el desmargen de **Pinnacle** (la casa de apuestas más eficiente del mundo) y detectar valor esperado positivo (**+EV**) para apostar en **Bet365** y casas recreativas.

El bot se ejecuta automáticamente todos los días entre las **12:00 PM y las 21:00 horas (hora de España peninsular)** mediante **GitHub Actions**:
1. **A las 12:00 PM:** Escaneo completo de las 14 ligas y envío del informe general a **Telegram**.
2. **De 13:00 a 21:00 horas (cada hora):** Monitorización ligera de cuotas para los picks activos hasta la hora de inicio de cada partido, enviando alertas inmediatas en cuanto una cuota alcanza el objetivo recomendado.

---

## 🚀 Arquitectura y Funcionamiento

```mermaid
flowchart TD
    Cron[GitHub Actions - 12:00 a 21:00 CET] --> Scheduler[run_scheduled_job.py]
    Scheduler -->|12:00 PM| Main[main.py: Escáner Diario 14 Ligas]
    Main --> Odds[The Odds API - 14 Ligas]
    Odds --> Filter[Filtro Partidos de Hoy]
    Filter --> Devig[Desmargen Pinnacle - Cuota Justa]
    Devig --> EV[Calculadora +EV]
    EV --> Telegram[Informe Diario en Telegram]
    EV --> State[(active_picks.json)]

    Scheduler -->|13:00 a 21:00| Monitor[monitor_picks.py: Monitor Horario]
    State --> Monitor
    Monitor -->|Solo ligas de picks activos| CheckOdds[Consulta Cuotas Mercado]
    CheckOdds --> Threshold{¿Cuota >= Objetivo?}
    Threshold -->|Sí| Alert[🚨 Alerta Urgente en Telegram]
    Threshold -->|No| Wait[Esperar siguiente hora]
```

### 1. Ligas Analizadas
1. 🇪🇸 LaLiga EA Sports (`soccer_spain_la_liga`)
2. 🇬🇧 Premier League (`soccer_epl`)
3. 🇮🇹 Serie A (`soccer_italy_serie_a`)
4. 🇩🇪 Bundesliga (`soccer_germany_bundesliga`)
5. 🇫🇷 Ligue 1 (`soccer_france_ligue_one`)
6. 🇳🇱 Eredivisie (`soccer_netherlands_eredivisie`)
7. 🇵🇹 Liga Portugal (`soccer_portugal_primeira_liga`)
8. 🇩🇰 Dinamarca - Superliga (`soccer_denmark_superliga`)
9. 🇳🇴 Noruega - Eliteserien (`soccer_norway_eliteserien`)
10. 🇧🇪 Bélgica - Pro League (`soccer_belgium_first_div`)
11. 🇹🇷 Turquía - Süper Lig (`soccer_turkey_super_league`)
12. 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Escocia - Premiership (`soccer_spl`)
13. 🇨🇭 Suiza - Super League (`soccer_switzerland_superleague`)
14. 🇸🇪 Suecia - Allsvenskan (`soccer_sweden_allsvenskan`)

### 2. Modelo Matemático (+EV y Kelly)
1. **Desmargen Proporcional (Multiplicative Devigging):**
   Para un partido con cuotas de Pinnacle $O_1, O_X, O_2$:
   $$p_i = \frac{1}{O_i}, \quad S = p_1 + p_X + p_2$$
   $$P_{\text{fair}, i} = \frac{p_i}{S}, \quad O_{\text{fair}, i} = \frac{1}{P_{\text{fair}, i}}$$
2. **Valor Esperado (+EV):**
   Para la cuota ofrecida en la casa recreativa $O_{\text{ofrecida}}$:
   $$\text{EV} = (P_{\text{fair}} \times O_{\text{ofrecida}}) - 1$$
   Si $\text{EV} > 0$, la apuesta tiene esperanza matemática positiva a largo plazo.
3. **Gestión de Stake (Criterio de Kelly Fraccional):**
   Utiliza *Quarter Kelly (25%)* para una gestión prudente del bankroll (máx 3.5% por apuesta).

---

## 🛠️ Configuración Rápida

### Paso 1: Conectar tu Telegram (Autodetección de Chat ID)
> **Importante:** Telegram no permite que un bot se envíe mensajes a sí mismo usando su nombre de usuario (`frankybet365bot`). Necesitas vincular tu ID numérico personal.

1. Abre Telegram y busca a tu bot: [https://t.me/frankybet365bot](https://t.me/frankybet365bot)
2. Pulsa el botón **INICIAR** (Start) o envíale un mensaje cualquiera (ej. `hola`).
3. En tu terminal ejecuta el autodetector:
   ```bash
   python3 detect_chat_id.py
   ```
4. El script detectará tu mensaje al instante, guardará tu Chat ID numérico en `.env` y te enviará un mensaje de bienvenida de prueba.

---

### Paso 2: Prueba Local
Ejecutar un escaneo completo de prueba o probar el monitor horario:
```bash
# Probar el escaneo de las 12:00 sin enviar a Telegram
python3 main.py --dry-run

# Probar solo una liga específica
python3 main.py --dry-run --league soccer_spain_la_liga

# Probar el monitor horario de seguimiento
python3 monitor_picks.py --dry-run

# Ejecutar el escaneo real y recibir el informe en Telegram
python3 main.py
```

---

## ☁️ Automatización Gratuita en GitHub Actions

Para que el bot se ejecute **totalmente solo todos los días de 12:00 a 21:00 horas** (sin necesidad de tener el ordenador encendido):

1. **Crea un repositorio en GitHub:**
   * Entra en [github.com/new](https://github.com/new) y crea un repositorio (público o privado).
2. **Sube el código:**
   ```bash
   git add .
   git commit -m "Initial commit - Bot de Apuestas con Valor (+EV) y Monitor Horario"
   git branch -M main
   git remote add origin https://github.com/TU_USUARIO/TU_REPOSITORIO.git
   git push -u origin main
   ```
3. **Configura los Secrets en GitHub:**
   * En tu repositorio de GitHub, ve a **Settings** > **Secrets and variables** > **Actions** > **New repository secret**.
   * Añade estos 3 secretos:
     * `ODDS_API_KEY`: `972b3c362634fcd8774a38e5b93ffd6f`
     * `TELEGRAM_BOT_TOKEN`: `9219638473:AAEYp5u89YbG2TjuyKeXrCJJIHvlSwqCLJo`
     * `TELEGRAM_CHAT_ID`: El ID numérico que obtuviste en el Paso 1.
4. **¡Listo!**
   * En la pestaña **Actions** de tu repositorio verás el flujo `Daily Betting Value Scanner & Hourly Tracker (+EV)`.
   * Se ejecutará automáticamente todos los días cada hora entre las **12:00 PM y las 21:00 CET (11:00 a 20:00 UTC)**.
   * También puedes pulsar **Run workflow** en cualquier momento para lanzarlo bajo demanda (eligiendo modo `auto`, `scan` o `monitor`).

---

## 🧪 Ejecutar Tests Unitarios
Para verificar la lógica matemática y de negocio:
```bash
python3 -m unittest test_bot.py
```
