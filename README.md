# ArgTV: Procesador Autónomo M3U y Generador EPG Unificado 🇦🇷

Sistema automatizado en Python diseñado para procesar, deduplicar, validar enlaces por HTTP en paralelo, clasificar canales en categorías en español y fusionar múltiples guías EPG (XMLTV).

---

## 🔗 Enlaces Públicos Permanentes para Kodi / IPTV

> [!NOTE]
> Estos enlaces se actualizan automáticamente todos los días mediante GitHub Actions y son 100% públicos para ser usados en cualquier reproductor o add-on.

### 🌐 Vía GitHub Pages (Recomendado)
- 📄 **Lista M3U:**
  ```text
  https://mmf-tv.github.io/playlist-tool/output/playlist.m3u
  ```
- 📺 **Guía EPG Comprimida (GZ):**
  ```text
  https://mmf-tv.github.io/playlist-tool/output/epg.xml.gz
  ```
- 📺 **Guía EPG Sin Comprimir (XML):**
  ```text
  https://mmf-tv.github.io/playlist-tool/output/epg.xml
  ```

### 📦 Vía GitHub Releases (Alternativa Directa)
- 📄 **Lista M3U:** `https://github.com/mmf-tv/playlist-tool/releases/download/latest/playlist.m3u`
- 📺 **Guía EPG (GZ):** `https://github.com/mmf-tv/playlist-tool/releases/download/latest/epg.xml.gz`

---

## 📖 Tutorial Completo: Configuración en Kodi (con IPTV Merge)

Este tutorial te guiará paso a paso desde cero para instalar **Kodi**, configurar el complemento **IPTV Merge** y cargar la lista M3U y la guía EPG de **ArgTV**.

### 📱 Paso 1: Instalación de Kodi

Descarga e instala **Kodi** (versión 20 Nexus o 21 Omega) según tu dispositivo:

* **Windows / macOS:** Descárgalo desde el sitio oficial [kodi.tv/download](https://kodi.tv/download).
* **Android / Android TV / Google TV:** Descárgalo desde **Google Play Store** o el APK oficial.
* **Amazon Fire TV Stick:** Instala la app *Downloader* y descarga el APK de Kodi de `kodi.tv/download`.

---

### 🧩 Paso 2: Instalación del Add-on "IPTV Merge"

**IPTV Merge** es el complemento más avanzado de Kodi para administrar listas de canales M3U y guías EPG. Permite fusionar múltiples listas sin sobreescribir configuraciones.

#### A. Activar "Orígenes Desconocidos" en Kodi
1. Abre **Kodi** y haz clic en el icono de **Ajustes** (engranaje ⚙️ en la esquina superior izquierda).
2. Entra en **Sistema** ➔ **Add-ons**.
3. Activa la opción **Fuentes desconocidas** (Unknown sources) y confirma el mensaje de aviso.

#### B. Agregar el Repositorio de SlyGuy
1. Vuelve a **Ajustes ⚙️** ➔ **Explorador de archivos** (File manager).
2. Haz clic en **Añadir fuente** (Add source).
3. En el campo de ruta URL, escribe exactamente:
   ```text
   https://slyguy.uk
   ```
4. En el nombre de la fuente escribe `SlyGuy` y haz clic en **OK**.

#### C. Instalar IPTV Merge desde el Repositorio
1. Vuelve al menú principal de Kodi y entra en **Add-ons**.
2. Haz clic en el icono de la caja abierta (esquina superior izquierda).
3. Selecciona **Instalar desde un archivo .zip** ➔ elige **SlyGuy** ➔ instala `repository.slyguy.zip`.
4. Una vez instalada la notificación del repositorio, selecciona **Instalar desde repositorio**.
5. Selecciona **SlyGuy Repository** ➔ **Add-ons de programa** (Program add-ons) ➔ **IPTV Merge**.
6. Haz clic en **Instalar** y acepta la instalación de dependencias (incluyendo *PVR IPTV Simple Client*).

---

### ⚙️ Paso 3: Cargar la Lista M3U y EPG de ArgTV en IPTV Merge

1. Ve a **Add-ons** ➔ **Add-ons de programa** ➔ Abre **IPTV Merge**.
2. **Agregar Lista M3U:**
   - Selecciona **Playlists** ➔ **Add Playlist**.
   - En **Source Type**, elige `URL`.
   - En **Playlist URL**, ingresa exactamente:
     ```text
     https://mmf-tv.github.io/playlist-tool/output/playlist.m3u
     ```
   - Haz clic en **OK**.
3. **Agregar Guía EPG:**
   - Vuelve al menú de IPTV Merge y selecciona **EPGs** ➔ **Add EPG**.
   - En **Source Type**, elige `URL`.
   - En **EPG URL**, ingresa exactamente:
     ```text
     https://mmf-tv.github.io/playlist-tool/output/epg.xml.gz
     ```
   - Haz clic en **OK**.
4. **Ejecutar la Fusión (Run Merge):**
   - En el menú principal de IPTV Merge, selecciona **Run Merge**.
   - IPTV Merge descargará los canales y la guía EPG, configurando automáticamente el cliente PVR de Kodi.
5. Reinicia Kodi. Al abrirlo, verás el menú **TV / Canales** con todos los canales clasificados por categorías y la programación EPG en vivo.

---

### 📺 Opción Alternativa: Configuración Directa con PVR IPTV Simple Client

Si prefieres usar directamente el add-on nativo de Kodi sin IPTV Merge:

1. Ve a **Ajustes ⚙️** ➔ **Add-ons** ➔ **Mis Add-ons** ➔ **Clientes PVR** ➔ **PVR IPTV Simple Client**.
2. Entra en **Configurar**:
   * **Pestaña General:**
     * Ubicación: `Ruta remota (Dirección de internet)`
     * URL de la lista M3U: `https://mmf-tv.github.io/playlist-tool/output/playlist.m3u`
   * **Pestaña Ajustes EPG:**
     * Ubicación: `Ruta remota (Dirección de internet)`
     * URL XMLTV: `https://mmf-tv.github.io/playlist-tool/output/epg.xml.gz`
3. Haz clic en **OK** y reinicia Kodi.

---

## 🛠️ Estructura del Proyecto

```text
ArgTV/
├── .github/
│   └── workflows/
│       └── update_playlist.yml   # Workflow automatizado diario y Releases
├── output/
│   ├── playlist.m3u              # Lista M3U final optimizada
│   ├── epg.xml.gz                # Guía EPG unificada comprimida (Kodi/TiviMate)
│   └── epg.xml                   # Guía EPG unificada XML
├── categorias_config.json        # Reglas de categorías y fuentes EPG
├── m3u_processor.py              # Motor autónomo en Python
├── requirements.txt              # Dependencias (requests)
└── README.md                     # Documentación y Tutoriales
```

---

## 🚀 Modos de Ejecución Local

### 1. Ejecución Completa (Verificación HLS + EPG)
```bash
python m3u_processor.py
```

### 2. Ejecución Rápida (Sin verificación HTTP)
```bash
python m3u_processor.py --skip-check
```
