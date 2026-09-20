# ArgTV: Procesador Autónomo M3U y Generador EPG Unificado

Sistema automatizado en Python diseñado para procesar, deduplicar, validar por HTTP, clasificar en categorías en español y fusionar guías EPG (XMLTV).

---

## Estructura del Proyecto

```text
ArgTV/
├── .github/
│   └── workflows/
│       └── update_playlist.yml    # Workflow para ejecución automática en GitHub Actions
├── output/
│   ├── playlist.m3u              # Lista M3U final con url-tvg integrado
│   ├── epg.xml.gz                # Guía EPG unificada comprimida (para Kodi/TiviMate)
│   └── epg.xml                   # Guía EPG unificada en texto plano XML
├── categorias_config.json        # Reglas de mapeo a español y fuentes EPG
├── m3u_processor.py              # Script autónomo ejecutable
├── requirements.txt              # Dependencias (requests, urllib3)
└── README.md                     # Documentación completa
```

---

## Fuentes M3U Incorporadas (6 en Total)

1. **IPTV-ORG Español**: `https://iptv-org.github.io/iptv/languages/spa.m3u`
2. **IPTV-ORG Argentina**: `https://iptv-org.github.io/iptv/countries/ar.m3u`
3. **IPTV-ORG La Plata**: `https://iptv-org.github.io/iptv/cities/arlpg.m3u`
4. **Radios Argentina (TV)**: `https://radiosargentina.com.ar/TVAR.m3u`
5. **M3U Chile / AR**: `https://m3u.cl/lista/AR.m3u`
6. **IP-TV App Argentina**: `https://ip-tv.app/m3u/Argentina_238.m3u`

---

## Fuentes EPG Fusionadas en `output/epg.xml.gz`

El script descarga y unifica las guías XMLTV de:
- **Argentina** (`AR1`)
- **España** (`ES1` / TDT)
- **México** (`MX1`)
- **Chile** (`CL1`)
- **Colombia** (`CO1`)
- **Perú** (`PE1`)
- **Uruguay** (`UY1`)
- **Pluto TV** (Latam, España y Global)
- **Plex TV**
- **Samsung TV Plus**
- **TDTChannels**

> **Optimización inteligente**: El motor EPG filtra los programas y solo conserva en el archivo final los canales activos presentes en la lista, reduciendo drásticamente el tamaño del archivo y acelerando la carga en Kodi y Smart TVs.

---

## Modos de Ejecución

### 1. Ejecución Completa (Local o Servidor)
```bash
python m3u_processor.py
```
> Descarga las 6 listas, deduplica, valida los enlaces por HTTP, clasifica las categorías en español, fusiona todas las guías EPG y genera `output/playlist.m3u` y `output/epg.xml.gz`.

### 2. Ejecución Rápida (Sin verificación HTTP)
```bash
python m3u_processor.py --skip-check
```

---

## Automatización en GitHub Actions

El archivo [`.github/workflows/update_playlist.yml`](file:///d:/ArgTV/.github/workflows/update_playlist.yml) está configurado para:
- Ejecutarse automáticamente todos los días a las **04:00 UTC** (01:00 AM Argentina).
- Permitir ejecución manual desde la pestaña **Actions** en GitHub (*workflow_dispatch*).
- Subir los archivos generados a `output/playlist.m3u` y `output/epg.xml.gz` para que puedas usarlos desde cualquier dispositivo mediante la URL Raw de GitHub.
