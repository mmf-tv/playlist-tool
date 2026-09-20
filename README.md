# ArgTV: Procesador Autónomo M3U y Generador EPG Unificado

Sistema automatizado en Python diseñado para procesar, deduplicar, validar por HTTP, clasificar en categorías en español y fusionar guías EPG (XMLTV).

---

## Estructura del Proyecto

```text
ArgTV/
├── .github/
│   └── workflows/
│       └── update_playlist.yml   # Workflow para ejecución automática y Releases
├── output/
│   ├── playlist.m3u              # Lista M3U final con url-tvg integrado
│   ├── epg.xml.gz                # Guía EPG unificada comprimida (para Kodi/TiviMate)
│   └── epg.xml                   # Guía EPG unificada XML
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

## Enlaces Públicos Permanentes (GitHub Releases)

Aunque el repositorio sea privado, los archivos finales se publican automáticamente en un **Release público**:

- 📄 **Lista M3U Pública**:
  ```text
  https://github.com/mmf-tv/playlist-tool/releases/download/latest/playlist.m3u
  ```
- 📺 **Guía EPG (XMLTV GZ) Pública**:
  ```text
  https://github.com/mmf-tv/playlist-tool/releases/download/latest/epg.xml.gz
  ```
- 📺 **Guía EPG (XMLTV XML) Pública**:
  ```text
  https://github.com/mmf-tv/playlist-tool/releases/download/latest/epg.xml
  ```

---

## Modos de Ejecución Local

### 1. Ejecución Completa
```bash
python m3u_processor.py
```

### 2. Ejecución Rápida (Sin verificación HTTP)
```bash
python m3u_processor.py --skip-check
```
