#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ArgTV: Procesador Autónomo de Listas M3U y Generador EPG Unificado
------------------------------------------------------------------
Diseñado para ejecución automatizada local y en CI/CD (GitHub Actions):
 1. Descarga listas M3U directamente desde fuentes remotas (IPTV-ORG, RadiosArgentina, etc.).
 2. Normaliza y deduplica canales ('smart') fusionando metadatos.
 3. Valida disponibilidad HTTP multihilo de cada canal descartando caídos.
 4. Reasigna categorías en español ('Películas', 'Argentina', 'La Plata', 'Deportes', etc.).
 5. Descarga y fusiona las guías EPG XMLTV (Argentina + España + México + Chile) en un único archivo
    consolidado 'epg.xml' / 'epg.xml.gz' filtrado para los canales activos.
 6. Exporta la lista final 'output/playlist.m3u' y 'output/epg.xml.gz'.
"""

import os
import re
import sys
import json
import time
import gzip
import shutil
import argparse
import urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set, Any

# Asegurar codificación UTF-8 en consola de Windows
if sys.platform.startswith("win"):
    try:
        if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    import requests
except ImportError:
    print("Error: El paquete 'requests' es requerido. Instálalo con: pip install requests")
    sys.exit(1)


# ==============================================================================
# CONFIGURACIÓN PREDETERMINADA
# ==============================================================================

DEFAULT_URLS = [
    # Fuentes IPTV-ORG
    "https://iptv-org.github.io/iptv/languages/spa.m3u",
    "https://iptv-org.github.io/iptv/countries/ar.m3u",
    "https://iptv-org.github.io/iptv/cities/arlpg.m3u",
    # Fuentes Nacionales y Regionales
    "https://radiosargentina.com.ar/TVAR.m3u",
    "https://m3u.cl/lista/AR.m3u",
    "https://ip-tv.app/m3u/Argentina_238.m3u",
    # Fuente Gist frantdse (Lista Vitile AR)
    "https://gist.githubusercontent.com/frantdse/54549f7b5c641de6567103bc90cdeab3/raw/",
    "https://gist.githubusercontent.com/frantdse/f6989518c73826ade6734c63c367af4c/raw/"
]

DEFAULT_EPG_SOURCES = [
    {"name": "Argentina (Nacional)", "url": "https://epgshare01.online/epgshare01/epg_ripper_AR1.xml.gz"},
    {"name": "España (TDT y Autonómicas)", "url": "https://epgshare01.online/epgshare01/epg_ripper_ES1.xml.gz"},
    {"name": "México (Latam)", "url": "https://epgshare01.online/epgshare01/epg_ripper_MX1.xml.gz"},
    {"name": "Chile", "url": "https://epgshare01.online/epgshare01/epg_ripper_CL1.xml.gz"},
    {"name": "Colombia", "url": "https://epgshare01.online/epgshare01/epg_ripper_CO1.xml.gz"},
    {"name": "Perú", "url": "https://epgshare01.online/epgshare01/epg_ripper_PE1.xml.gz"},
    {"name": "Uruguay", "url": "https://epgshare01.online/epgshare01/epg_ripper_UY1.xml.gz"},
    {"name": "Pluto TV (Latam y Global)", "url": "https://i.mjh.nz/PlutoTV/all.xml.gz"},
    {"name": "Plex TV", "url": "https://epgshare01.online/epgshare01/epg_ripper_PLEX1.xml.gz"},
    {"name": "Samsung TV Plus", "url": "https://i.mjh.nz/SamsungTVPlus/all.xml.gz"},
    {"name": "TDTChannels", "url": "https://www.tdtchannels.com/epg/TV.xml.gz"}
]

DEFAULT_CONFIG_FILE = "categorias_config.json"
DEFAULT_OUTPUT_PLAYLIST = "output/playlist.m3u"
DEFAULT_OUTPUT_EPG_GZ = "output/epg.xml.gz"
DEFAULT_OUTPUT_EPG_XML = "output/epg.xml"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 VLC/3.0.18 LibVLC/3.0.18",
    "Accept": "*/*",
    "Connection": "keep-alive"
}

DEFAULT_CATEGORY_RULES = {
    "La Plata": [
        "la plata", "laplata", "arlpg", "arlpg.m3u", "realpolitik", "tv universidad",
        "unlp", "somos la plata", "canal 2 la plata", "diario el dia"
    ],
    "Películas": [
        "películas", "peliculas", "película", "pelicula", "movies", "movie", "cinema",
        "cine", "films", "film", "cine y series", "hbo", "star channel", "star+", "paramount",
        "warner", "cinemax", "axn", "fx", "universal", "tnt", "space", "amc", "sony channel",
        "studio universal", "golden", "tcm", "europa europa", "cinecanal", "multipremier"
    ],
    "Deportes": [
        "deportes", "sports", "deporte", "sport", "futbol", "fútbol", "espn", "fox sports",
        "tyc sports", "directv sports", "dsports", "dazn", "nba", "nfl", "tnt sports",
        "gol tv", "bein", "eurosport", "ufc", "wwe", "motogp", "f1", "formula 1", "tenis",
        "tennis", "liga", "champions", "conmebol", "libertadores"
    ],
    "Noticias": [
        "noticias", "news", "noticieros", "informacion", "tn", "c5n", "la nacion", "ln+",
        "cronica", "a24", "cnn", "bbc", "rt", "telesur", "euronews", "dw", "france 24",
        "bloomberg", "canal 26", "ip noticias"
    ],
    "Infantil": [
        "infantil", "infantiles", "kids", "children", "animacion", "dibujos", "cartoon",
        "disney", "disney channel", "disney junior", "nickelodeon", "nick", "nick jr",
        "cartoon network", "boomerang", "discovery kids", "tooncami", "cartoonito", "pakapaka",
        "baby tv", "clan"
    ],
    "Música": [
        "musica", "música", "music", "mtv", "vh1", "htv", "cm", "quiero", "muchmusic",
        "trace", "billboard", "stingray", "kiss", "sol musica", "fm", "radio"
    ],
    "Documentales": [
        "documentales", "documental", "documentary", "cultura", "culture", "discovery",
        "national geographic", "nat geo", "history", "history 2", "animal planet", "investigation",
        "natgeo wild", "h2", "smithsonian", "discovery science", "discovery theater", "encuentro"
    ],
    "Internacional": [
        "internacional", "international", "world", "latam", "usa", "espana", "españa",
        "mexico", "méxico", "colombia", "chile", "uruguay", "peru", "perú", "brasil",
        "bolivia", "venezuela", "ecuador", "paraguay", ".es@", ".mx@", ".cl@", ".co@",
        ".pe@", ".uy@", ".py@", ".bo@", ".ve@", ".ec@", ".br@"
    ],
    "Argentina": [
        "argentina", "ar.m3u", "tvar", "tvar.m3u", "ar@sd", "ar@hd", ".ar@", "telefe", "eltrece", "el trece",
        "canal 9", "el nueve", "america tv", "américa tv", "tv publica", "tv pública",
        "net tv", "bravo tv", "canal 7", "tda", "buenos aires", "caba", "cd cd aut bs as", "ba pcia bs as",
        "cordoba", "cba", "santa fe", "mendoza", "rosario", "tucuman", "salta", "misiones", "corrientes",
        "chaco", "neuquen", "rio negro", "chubut", "tierra del fuego", "ushuaia", "mar del plata", "bahia blanca", "bariloche"
    ],
    "Entretenimiento": [
        "entretenimiento", "variedades", "entertainment", "general", "comedy", "e!", "tlc",
        "telenovelas", "novelas", "comedy central", "lifetime", "glitz", "tbs", "trutv",
        "las estrellas", "telemundo", "univision"
    ],
    "Religión": [
        "religion", "religión", "religious", "cristiano", "evangelico", "catolico", "enlace", "ewtn"
    ],
    "Otros": []
}


# ==============================================================================
# MODELO DE CANAL
# ==============================================================================

@dataclass
class Channel:
    name: str
    url: str
    original_group: str = "Sin Categoría"
    mapped_group: str = "Otros"
    tvg_id: str = ""
    tvg_name: str = ""
    tvg_logo: str = ""
    tvg_epg: str = ""
    tvg_country: str = ""
    tvg_language: str = ""
    attributes: Dict[str, str] = field(default_factory=dict)
    extra_tags: List[str] = field(default_factory=list)
    source_name: str = ""
    is_alive: bool = True
    http_status: Optional[int] = None
    response_time: float = 0.0
    error_message: str = ""


# ==============================================================================
# PARSER M3U
# ==============================================================================

class M3UParser:
    """Parsea archivos y URLs M3U extrayendo todos los metadatos de canal."""

    ATTR_REGEX = re.compile(r'([\w-]+)=(?:"([^"]*)"|(\S+))')

    @classmethod
    def parse_content(cls, content: str, source_name: str = "") -> List[Channel]:
        channels: List[Channel] = []
        lines = [line.strip() for line in content.splitlines() if line.strip()]

        current_channel: Optional[Channel] = None
        extra_tags: List[str] = []

        for line in lines:
            if line.startswith("#EXTM3U"):
                continue
            elif line.startswith("#EXTINF:"):
                current_channel = cls._parse_extinf(line, source_name)
                current_channel.extra_tags = list(extra_tags)
                extra_tags.clear()
            elif line.startswith("#"):
                extra_tags.append(line)
            else:
                if current_channel:
                    current_channel.url = line
                    channels.append(current_channel)
                    current_channel = None
                else:
                    ch = Channel(
                        name=cls._extract_name_from_url(line),
                        url=line,
                        source_name=source_name,
                        extra_tags=list(extra_tags)
                    )
                    channels.append(ch)
                    extra_tags.clear()

        return channels

    @classmethod
    def _parse_extinf(cls, line: str, source_name: str) -> Channel:
        comma_idx = line.rfind(",")
        if comma_idx != -1:
            meta_part = line[:comma_idx]
            name_part = line[comma_idx + 1:].strip()
        else:
            meta_part = line
            name_part = "Canal Sin Nombre"

        attributes = {}
        for match in cls.ATTR_REGEX.finditer(meta_part):
            key = match.group(1).lower()
            val = match.group(2) if match.group(2) is not None else match.group(3)
            attributes[key] = val or ""

        tvg_id = attributes.get("tvg-id", "")
        tvg_name = attributes.get("tvg-name", "")
        tvg_logo = attributes.get("tvg-logo", "")
        tvg_epg = attributes.get("tvg-epg", "") or attributes.get("tvg-chno", "")
        tvg_country = attributes.get("tvg-country", "")
        tvg_language = attributes.get("tvg-language", "")
        group_title = attributes.get("group-title", "Sin Categoría").strip()

        if not name_part and tvg_name:
            name_part = tvg_name
        elif not name_part:
            name_part = "Canal Sin Nombre"

        return Channel(
            name=name_part,
            url="",
            original_group=group_title if group_title else "Sin Categoría",
            tvg_id=tvg_id,
            tvg_name=tvg_name,
            tvg_logo=tvg_logo,
            tvg_epg=tvg_epg,
            tvg_country=tvg_country,
            tvg_language=tvg_language,
            attributes=attributes,
            source_name=source_name
        )

    @classmethod
    def _extract_name_from_url(cls, url: str) -> str:
        parsed = urllib.parse.urlparse(url)
        path = parsed.path.split("/")[-1]
        name = os.path.splitext(path)[0]
        return name if name else "Canal Desconocido"

    @classmethod
    def load_file(cls, filepath: str) -> List[Channel]:
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        content = None
        for enc in encodings:
            try:
                with open(filepath, 'r', encoding=enc) as f:
                    content = f.read()
                break
            except (UnicodeDecodeError, OSError):
                continue

        if content is None:
            raise ValueError(f"No se pudo leer '{filepath}' con codificaciones estándar.")

        return cls.parse_content(content, source_name=os.path.basename(filepath))

    @classmethod
    def load_url(cls, url: str, timeout: float = 15.0) -> List[Channel]:
        source_label = url.split("/")[-1] if "/" in url else url
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        resp.raise_for_status()
        return cls.parse_content(resp.text, source_name=source_label)


# ==============================================================================
# DEDUPLICADOR Y FUSIONADOR INTELIGENTE
# ==============================================================================

class Deduplicator:
    """Normaliza, elimina duplicados y fusiona metadatos enriquecidos."""

    @staticmethod
    def normalize_url(url: str) -> str:
        if not url:
            return ""
        url = url.strip()
        try:
            parts = urllib.parse.urlsplit(url)
            scheme = parts.scheme.lower()
            netloc = parts.netloc.lower()
            if (scheme == 'http' and netloc.endswith(':80')) or (scheme == 'https' and netloc.endswith(':443')):
                netloc = netloc.rsplit(':', 1)[0]
            path = parts.path
            if path.endswith('/') and len(path) > 1:
                path = path[:-1]
            return urllib.parse.urlunsplit((scheme, netloc, path, parts.query, ""))
        except Exception:
            return url.strip().lower()

    @staticmethod
    def normalize_name(name: str) -> str:
        if not name:
            return ""
        n = name.strip()
        n = re.sub(r'[\(\[]\s*(?:1080p|720p|480p|360p|4k|fhd|hd|sd|hevc|h264|h265|not 24/7|geo-blocked|offline|vivo|live)\s*[\)\]]', '', n, flags=re.IGNORECASE)
        n = re.sub(r'\b(?:1080p|720p|480p|4k|fhd|hd|sd)\b', '', n, flags=re.IGNORECASE)
        n = re.sub(r'[-–—]\s*(?:argentina|caba|buenos aires|fm|tv|tv cable|ctv)\b.*$', '', n, flags=re.IGNORECASE)
        n = re.sub(r'[^\w\s]', ' ', n)
        n = re.sub(r'\s+', ' ', n).strip().lower()
        return n

    @classmethod
    def deduplicate(cls, channels: List[Channel], mode: str = "smart") -> Tuple[List[Channel], int]:
        seen_urls: Dict[str, Channel] = {}
        seen_keys: Dict[str, Channel] = {}
        unique_list: List[Channel] = []
        duplicates_count = 0

        for ch in channels:
            # Upgrade de URLs conocidas con problemas de compresión GZIP o inestabilidad
            if "eltrece" in ch.url.lower() or "eltrece" in ch.tvg_id.lower() or "el trece" in ch.name.lower():
                if "vodgc.net" in ch.url.lower():
                    ch.url = "https://livetrx01.vodgc.net/eltrecetv/index.m3u8"

            norm_url = cls.normalize_url(ch.url)
            norm_name = cls.normalize_name(ch.name)
            raw_tvg_id = ch.tvg_id.strip().lower()
            clean_tvg_id = re.sub(r'@[a-zA-Z0-9_-]+', '', raw_tvg_id)

            if norm_url in seen_urls:
                existing = seen_urls[norm_url]
                cls._merge_metadata(existing, ch)
                duplicates_count += 1
                continue

            if mode == "smart":
                key = None
                if clean_tvg_id and clean_tvg_id not in ["undefined", "none", "null"]:
                    key = f"id:{clean_tvg_id}"
                elif norm_name and len(norm_name) > 3:
                    key = f"name:{norm_name}"

                if key and key in seen_keys:
                    existing = seen_keys[key]
                    cls._merge_metadata(existing, ch)
                    duplicates_count += 1
                    continue

                if key:
                    seen_keys[key] = ch

            seen_urls[norm_url] = ch
            unique_list.append(ch)

        return unique_list, duplicates_count

    @staticmethod
    def _merge_metadata(target: Channel, source: Channel) -> None:
        # Preferir URLs HTTPS o CDNs oficiales frente a IPs crudas inseguras o inestables
        target_url_lower = target.url.lower()
        source_url_lower = source.url.lower()
        cdn_domains = ["vodgc.net", "rudo.video", "qaotic.net", "mux.dev", "streamlock.net", "dps.live", "m3u.cl"]
        is_target_cdn = any(domain in target_url_lower for domain in cdn_domains)
        is_source_cdn = any(domain in source_url_lower for domain in cdn_domains)
        is_target_raw_ip = bool(re.search(r'http://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', target_url_lower))
        is_source_raw_ip = bool(re.search(r'http://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', source_url_lower))

        if (not is_target_cdn and is_source_cdn) or (is_target_raw_ip and not is_source_raw_ip):
            target.url = source.url

        if not target.tvg_logo and source.tvg_logo:
            target.tvg_logo = source.tvg_logo
        if not target.tvg_id and source.tvg_id:
            target.tvg_id = source.tvg_id
        if not target.tvg_name and source.tvg_name:
            target.tvg_name = source.tvg_name
        if not target.tvg_epg and source.tvg_epg:
            target.tvg_epg = source.tvg_epg
        if not target.tvg_country and source.tvg_country:
            target.tvg_country = source.tvg_country
        if not target.tvg_language and source.tvg_language:
            target.tvg_language = source.tvg_language
        for tag in source.extra_tags:
            if tag not in target.extra_tags:
                target.extra_tags.append(tag)


# ==============================================================================
# REASIGNADOR Y CLASIFICADOR DE CATEGORÍAS
# ==============================================================================

class CategoryMapper:
    """Mapea categorías usando reglas JSON prioritarias en español."""

    def __init__(self, rules: Optional[Dict[str, List[str]]] = None, default_category: str = "Otros"):
        self.rules = rules if rules is not None else DEFAULT_CATEGORY_RULES
        self.default_category = default_category
        self._compiled_rules: List[Tuple[str, List[re.Pattern]]] = []

        for target_cat, patterns in self.rules.items():
            compiled = []
            for p in patterns:
                p_clean = p.strip()
                if not p_clean:
                    continue
                escaped = re.escape(p_clean)
                try:
                    compiled.append(re.compile(rf'\b{escaped}\b', re.IGNORECASE))
                except Exception:
                    compiled.append(re.compile(escaped, re.IGNORECASE))
            self._compiled_rules.append((target_cat, compiled))

    def map_channel(self, channel: Channel) -> str:
        orig_group = channel.original_group.lower().strip()
        channel_name = channel.name.lower().strip()
        tvg_name = channel.tvg_name.lower().strip()
        tvg_id = channel.tvg_id.lower().strip()
        source_name = channel.source_name.lower().strip()
        tvg_country = channel.tvg_country.lower().strip()

        combined_text = f"{orig_group} {channel_name} {tvg_name} {tvg_id} {source_name} {tvg_country}"

        # 1. Coincidencia exacta
        for target_cat in self.rules.keys():
            if orig_group == target_cat.lower():
                channel.mapped_group = target_cat
                return target_cat

        # 2. Coincidencia por patrones y palabras clave ordenadas
        for target_cat, regex_list in self._compiled_rules:
            for regex in regex_list:
                if regex.search(combined_text) or regex.search(orig_group):
                    channel.mapped_group = target_cat
                    return target_cat

        channel.mapped_group = self.default_category
        return self.default_category

    def map_all(self, channels: List[Channel]) -> None:
        for ch in channels:
            self.map_channel(ch)


# ==============================================================================
# VERIFICADOR HTTP DE ENLACES
# ==============================================================================

class StreamChecker:
    """Verifica disponibilidad de streams mediante solicitudes HTTP ultrarrápidas."""

    def __init__(self, timeout: float = 5.0, user_agent: Optional[str] = None):
        self.timeout = timeout
        self.headers = dict(DEFAULT_HEADERS)
        if user_agent:
            self.headers["User-Agent"] = user_agent

    def check_link(self, channel: Channel) -> Channel:
        url = channel.url.strip()
        if not url or not (url.startswith("http://") or url.startswith("https://")):
            if any(url.startswith(proto) for proto in ["rtmp://", "rtsp://", "udp://", "mms://", "acestream://"]):
                channel.is_alive = True
                channel.http_status = 200
                channel.error_message = "Protocolo admitido"
                return channel
            channel.is_alive = False
            channel.error_message = "Protocolo no soportado"
            return channel

        start_time = time.time()

        try:
            with requests.Session() as session:
                session.headers.update(self.headers)
                session.headers["Accept-Encoding"] = "identity"
                req_headers = {"Range": "bytes=0-2048"}

                try:
                    response = session.get(url, headers=req_headers, stream=True, allow_redirects=True, timeout=self.timeout)
                except requests.RequestException as get_err:
                    channel.is_alive = False
                    channel.error_message = f"Conexión fallida: {str(get_err)}"
                    channel.response_time = round(time.time() - start_time, 3)
                    return channel

                elapsed = time.time() - start_time
                channel.response_time = round(elapsed, 3)

                if response and response.status_code in [200, 206, 301, 302, 307, 308]:
                    content_chunk = b""
                    try:
                        content_chunk = response.raw.read(2048) if hasattr(response, 'raw') and response.raw else response.content[:2048]
                    except Exception:
                        content_chunk = response.content[:2048] if hasattr(response, 'content') else b""

                    is_hls_url = ".m3u" in url.lower() or "hls" in url.lower() or "playlist" in url.lower()
                    has_extm3u = b"#EXTM3U" in content_chunk or b"#EXT-X-" in content_chunk
                    is_html_error = b"<html" in content_chunk.lower() or b"<body" in content_chunk.lower() or b"404 not found" in content_chunk.lower()

                    if is_html_error:
                        channel.is_alive = False
                        channel.http_status = 404
                        channel.error_message = "Página de error HTML"
                    elif is_hls_url and not has_extm3u and len(content_chunk) < 50:
                        channel.is_alive = False
                        channel.http_status = 404
                        channel.error_message = "Respuesta HLS vacía/inválida"
                    else:
                        channel.is_alive = True
                        channel.http_status = response.status_code

                    try:
                        response.close()
                    except Exception:
                        pass
                else:
                    channel.is_alive = False
                    channel.http_status = response.status_code if response else 0
                    channel.error_message = f"HTTP {channel.http_status}"

        except Exception as e:
            channel.is_alive = False
            channel.response_time = round(time.time() - start_time, 3)
            channel.error_message = str(e)

        return channel

    def verify_channels(self, channels: List[Channel], max_workers: int = 35, progress_callback=None) -> Tuple[List[Channel], List[Channel]]:
        alive_channels: List[Channel] = []
        dead_channels: List[Channel] = []
        total = len(channels)
        completed = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_channel = {executor.submit(self.check_link, ch): ch for ch in channels}

            for future in as_completed(future_to_channel):
                ch = future.result()
                completed += 1
                if ch.is_alive:
                    alive_channels.append(ch)
                else:
                    dead_channels.append(ch)

                if progress_callback:
                    progress_callback(completed, total, ch)

        return alive_channels, dead_channels


# ==============================================================================
# FUSIONADOR Y GESTOR DE GUÍAS EPG (XMLTV)
# ==============================================================================

class EPGManager:
    """
    Descarga, procesa y fusiona múltiples fuentes EPG (XMLTV) en un único archivo
    consolidado y comprimido (epg.xml.gz), optimizado para los canales activos.
    """

    @classmethod
    def normalize_key(cls, text: str) -> str:
        if not text:
            return ""
        t = re.sub(r'[\(\[]\s*(?:1080p|720p|480p|360p|4k|fhd|hd|sd|canal|tv|argentina|panregional|south)\s*[\)\]]', '', text, flags=re.IGNORECASE)
        t = re.sub(r'\b(?:canal|tv|hd|sd|fhd)\b', '', t, flags=re.IGNORECASE)
        t = re.sub(r'@[a-zA-Z0-9_-]+', '', t)
        t = re.sub(r'[^\w\s]', '', t)
        return re.sub(r'\s+', '', t).strip().lower()

    @classmethod
    def merge_and_save_epg(
        cls,
        epg_sources: List[Dict[str, str]],
        active_channels: List[Channel],
        output_xml_path: str,
        output_gz_path: str
    ) -> Dict[str, Any]:
        print(f"\n[EPG] Fusionando guías de programación para {len(active_channels)} canales...")

        channel_norm_map: Dict[str, List[Channel]] = {}
        for ch in active_channels:
            keys = set()
            if ch.tvg_id:
                keys.add(cls.normalize_key(ch.tvg_id))
            if ch.tvg_name:
                keys.add(cls.normalize_key(ch.tvg_name))
            if ch.name:
                keys.add(cls.normalize_key(ch.name))

            for k in keys:
                if k and len(k) >= 3:
                    channel_norm_map.setdefault(k, []).append(ch)

        root_tv = ET.Element("tv")
        root_tv.set("generator-info-name", "ArgTV EPG Generator")
        root_tv.set("generator-info-url", "https://github.com/ArgTV")

        merged_channels_count = 0
        merged_programmes_count = 0
        matched_xmltv_cids: Set[str] = set()
        matched_cids_lower: Set[str] = set()

        for source in epg_sources:
            name = source.get("name", "Guía")
            url = source.get("url", "").strip()
            if not url:
                continue

            print(f" -> Descargando y procesando EPG: {name} ({url.split('/')[-1]})...")
            try:
                resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=30.0, stream=True)
                resp.raise_for_status()

                raw_bytes = resp.content
                if url.endswith(".gz") or (len(raw_bytes) > 2 and raw_bytes[:2] == b'\x1f\x8b'):
                    try:
                        raw_bytes = gzip.decompress(raw_bytes)
                    except Exception as gz_err:
                        print(f"    [!] Error al descomprimir gzip {name}: {gz_err}")
                        continue

                try:
                    tree = ET.fromstring(raw_bytes)
                except ET.ParseError as pe:
                    print(f"    [!] Error al parsear XML de {name}: {pe}")
                    continue

                source_channels_matched = 0
                source_programmes_matched = 0

                for elem in tree.findall("channel"):
                    cid = elem.get("id", "").strip()
                    if not cid:
                        continue

                    display_names = [d.text for d in elem.findall("display-name") if d.text]
                    xml_keys = {cls.normalize_key(cid)}
                    for dn in display_names:
                        xml_keys.add(cls.normalize_key(dn))

                    is_match = False
                    for xk in xml_keys:
                        if xk in channel_norm_map:
                            is_match = True
                            for target_ch in channel_norm_map[xk]:
                                if not target_ch.tvg_id or "@" in target_ch.tvg_id or len(target_ch.tvg_id) < 3:
                                    target_ch.tvg_id = cid
                            break

                    if is_match or not active_channels:
                        if cid.lower() not in matched_cids_lower:
                            matched_cids_lower.add(cid.lower())
                            matched_xmltv_cids.add(cid)
                            root_tv.append(elem)
                            merged_channels_count += 1
                            source_channels_matched += 1

                for elem in tree.findall("programme"):
                    prog_channel = elem.get("channel", "").strip()
                    if prog_channel and (prog_channel in matched_xmltv_cids or prog_channel.lower() in matched_cids_lower):
                        root_tv.append(elem)
                        merged_programmes_count += 1
                        source_programmes_matched += 1

                print(f"    ✔ {source_channels_matched} canales y {source_programmes_matched} programas vinculados.")

            except Exception as e:
                print(f"    [!] Fallo al procesar {name}: {e}")

        out_dir = os.path.dirname(output_xml_path) or "."
        os.makedirs(out_dir, exist_ok=True)

        xml_tree = ET.ElementTree(root_tv)
        try:
            xml_tree.write(output_xml_path, encoding="utf-8", xml_declaration=True)
            xml_size_mb = round(os.path.getsize(output_xml_path) / (1024 * 1024), 2)
            print(f"✔ Guía EPG XML consolidada: '{output_xml_path}' ({xml_size_mb} MB)")

            with open(output_xml_path, 'rb') as f_in:
                with gzip.open(output_gz_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            gz_size_kb = round(os.path.getsize(output_gz_path) / 1024, 1)
            print(f"✔ Guía EPG GZIP comprimida: '{output_gz_path}' ({gz_size_kb} KB)")

        except Exception as write_err:
            print(f"[!] Error al escribir archivos EPG: {write_err}")

        return {
            "total_channels": merged_channels_count,
            "total_programmes": merged_programmes_count,
            "xml_path": output_xml_path,
            "gz_path": output_gz_path
        }


# ==============================================================================
# EXPORTADOR M3U
# ==============================================================================

class M3UExporter:
    """Escribe la lista M3U final con encabezado url-tvg integrado."""

    @classmethod
    def export(
        cls,
        channels: List[Channel],
        output_file: str,
        epg_references: Optional[List[str]] = None,
        sort_by_category: bool = True
    ) -> None:
        if sort_by_category:
            channels = sorted(channels, key=lambda c: (c.mapped_group.lower(), c.name.lower()))

        epg_refs = [u.strip() for u in (epg_references or []) if u.strip()]
        if epg_refs:
            epg_joined = ",".join(epg_refs)
            header_line = f'#EXTM3U url-tvg="{epg_joined}" x-tvg-url="{epg_joined}"'
        else:
            header_line = "#EXTM3U"

        lines = [header_line]

        for ch in channels:
            attrs = []
            if ch.tvg_id:
                attrs.append(f'tvg-id="{ch.tvg_id}"')
            if ch.tvg_name:
                attrs.append(f'tvg-name="{ch.tvg_name}"')
            if ch.tvg_logo:
                attrs.append(f'tvg-logo="{ch.tvg_logo}"')
            if ch.tvg_epg:
                attrs.append(f'tvg-epg="{ch.tvg_epg}"')
            if ch.tvg_country:
                attrs.append(f'tvg-country="{ch.tvg_country}"')
            if ch.tvg_language:
                attrs.append(f'tvg-language="{ch.tvg_language}"')

            attrs.append(f'group-title="{ch.mapped_group}"')

            has_ua = False
            for k, v in ch.attributes.items():
                if k.lower() in ["http-user-agent", "user-agent"]:
                    has_ua = True
                if k not in ["tvg-id", "tvg-name", "tvg-logo", "tvg-epg", "tvg-country", "tvg-language", "group-title"]:
                    attrs.append(f'{k}="{v}"')

            if not has_ua:
                attrs.append('http-user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"')

            attr_str = " " + " ".join(attrs) if attrs else ""
            extinf_line = f'#EXTINF:-1{attr_str},{ch.name}'
            lines.append(extinf_line)

            for extra in ch.extra_tags:
                lines.append(extra)

            lines.append(ch.url)

        out_dir = os.path.dirname(output_file) or "."
        os.makedirs(out_dir, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


# ==============================================================================
# MOTOR PRINCIPAL
# ==============================================================================

class M3UProcessor:
    """Ejecutor integral del pipeline M3U y EPG."""

    def __init__(
        self,
        config_file: Optional[str] = None,
        timeout: float = 5.0,
        max_workers: int = 35,
        user_agent: Optional[str] = None,
        default_category: str = "Otros"
    ):
        self.timeout = timeout
        self.max_workers = max_workers
        self.user_agent = user_agent
        self.default_category = default_category
        self.config_path = config_file or DEFAULT_CONFIG_FILE
        self.category_rules, self.epg_sources = self._load_config(self.config_path)
        self.mapper = CategoryMapper(self.category_rules, default_category=self.default_category)
        self.checker = StreamChecker(timeout=self.timeout, user_agent=self.user_agent)

    def _load_config(self, config_file: str) -> Tuple[Dict[str, List[str]], List[Dict[str, str]]]:
        possible_paths = [
            config_file,
            os.path.join(os.path.dirname(os.path.abspath(__file__)), config_file),
            os.path.join(os.getcwd(), config_file)
        ]
        categories = DEFAULT_CATEGORY_RULES
        epg_sources = list(DEFAULT_EPG_SOURCES)

        for p in possible_paths:
            if os.path.isfile(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                        print(f"✔ Configuración cargada desde: '{p}'")
                        if "categories" in cfg:
                            categories = cfg["categories"]
                        if "epg_sources" in cfg and isinstance(cfg["epg_sources"], list):
                            epg_sources = cfg["epg_sources"]
                        elif "epg_urls" in cfg and isinstance(cfg["epg_urls"], list):
                            epg_sources = [{"name": u.split('/')[-1], "url": u} for u in cfg["epg_urls"]]
                        return categories, epg_sources
                except Exception as e:
                    print(f"[!] Error leyendo '{p}': {e}. Usando reglas por defecto.")
                    break

        print(f"[i] Archivo '{config_file}' no encontrado. Usando configuración predeterminada.")
        return categories, epg_sources

    def process(
        self,
        sources: List[str],
        output_file: str = DEFAULT_OUTPUT_PLAYLIST,
        output_epg_xml: str = DEFAULT_OUTPUT_EPG_XML,
        output_epg_gz: str = DEFAULT_OUTPUT_EPG_GZ,
        verify_links: bool = True,
        deduplicate: bool = True,
        dedupe_mode: str = "smart",
        sort_by_category: bool = True
    ) -> Dict[str, Any]:
        print("\n" + "=" * 68)
        print(" PIPELINE DE ACTUALIZACIÓN AUTOMÁTICA DE LISTAS M3U Y EPG")
        print("=" * 68)

        # ----------------------------------------------------------------------
        # PASO 1: DESCARGA DE FUENTES M3U
        # ----------------------------------------------------------------------
        print(f"\n[1/5] Descargando y cargando {len(sources)} listas M3U fuentes...")
        all_channels: List[Channel] = []

        for src in sources:
            src = src.strip()
            if not src:
                continue

            if src.startswith("http://") or src.startswith("https://"):
                print(f" -> Descargando URL: {src}")
                try:
                    channels = M3UParser.load_url(src, timeout=max(self.timeout * 3, 15.0))
                    all_channels.extend(channels)
                    print(f"    Canales extraídos: {len(channels)}")
                except Exception as e:
                    print(f"    [!] Error al descargar {src}: {e}")

            elif os.path.isdir(src):
                print(f" -> Escaneando carpeta local: {src}")
                for root, _, files in os.walk(src):
                    for file in files:
                        if file.lower().endswith((".m3u", ".m3u8")):
                            full_path = os.path.join(root, file)
                            try:
                                channels = M3UParser.load_file(full_path)
                                all_channels.extend(channels)
                                print(f"    - {file}: {len(channels)} canales")
                            except Exception as e:
                                print(f"    [!] Error leyendo {file}: {e}")

            elif os.path.isfile(src):
                print(f" -> Leyendo archivo local: {src}")
                try:
                    channels = M3UParser.load_file(src)
                    all_channels.extend(channels)
                    print(f"    Canales extraídos: {len(channels)}")
                except Exception as e:
                    print(f"    [!] Error leyendo {src}: {e}")
            else:
                print(f"    [!] Fuente no válida o no encontrada: {src}")

        print(f"\nTotal bruto de canales encontrados: {len(all_channels)}")

        if not all_channels:
            print("[!] No se encontraron canales disponibles para procesar.")
            return {"total_loaded": 0, "alive": 0, "dead": 0, "categories": {}}

        # ----------------------------------------------------------------------
        # PASO 2: DEDUPLICACIÓN INTELIGENTE Y FUSIÓN DE METADATOS
        # ----------------------------------------------------------------------
        if deduplicate:
            print(f"\n[2/5] Deduplicando canales (Modo: '{dedupe_mode}') y enriqueciendo metadatos...")
            all_channels, duplicates_removed = Deduplicator.deduplicate(all_channels, mode=dedupe_mode)
            print(f"✔ Canales repetidos eliminados/fusionados: {duplicates_removed} (Canales únicos: {len(all_channels)})")
        else:
            print("\n[2/5] Deduplicación omitida (--no-dedupe).")

        # ----------------------------------------------------------------------
        # PASO 3: VALIDACIÓN HTTP DE CONECTIVIDAD
        # ----------------------------------------------------------------------
        alive_channels: List[Channel] = []
        dead_channels: List[Channel] = []

        if verify_links:
            print(f"\n[3/5] Verificando conectividad HTTP con {self.max_workers} hilos concurrentes...")

            def progress(completed, total, ch):
                status_symbol = "[OK]" if ch.is_alive else "[X]"
                status_text = f"HTTP {ch.http_status}" if ch.http_status else (ch.error_message[:14] if ch.error_message else "Error")
                bar_len = 20
                filled_len = int(bar_len * completed // total)
                bar = '#' * filled_len + '-' * (bar_len - filled_len)
                name_clean = re.sub(r'[^\x00-\x7F]+', '', ch.name)
                name_display = (name_clean[:18] + '..') if len(name_clean) > 20 else name_clean
                sys.stdout.write(f"\r  [{bar}] {completed}/{total} ({completed*100//total}%) | {status_symbol} {name_display:<20} ({status_text})")
                sys.stdout.flush()

            alive_channels, dead_channels = self.checker.verify_channels(
                all_channels,
                max_workers=self.max_workers,
                progress_callback=progress
            )
            print()
            print(f"Canales funcionales (activos): {len(alive_channels)}")
            print(f"Canales caídos (descartados): {len(dead_channels)}")
        else:
            print("\n[3/5] Verificación de enlaces omitida (--skip-check).")
            alive_channels = all_channels

        # ----------------------------------------------------------------------
        # PASO 4: APLICAR CATEGORIZACIÓN EN ESPAÑOL
        # ----------------------------------------------------------------------
        print("\n[4/5] Clasificando y normalizando categorías en español...")
        self.mapper.map_all(alive_channels)

        category_counts: Dict[str, int] = {}
        for ch in alive_channels:
            category_counts[ch.mapped_group] = category_counts.get(ch.mapped_group, 0) + 1

        for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  • {cat:<22}: {count:>4} canales")

        # ----------------------------------------------------------------------
        # PASO 5: FUSIÓN DE GUÍAS EPG Y EXPORTACIÓN FINAL
        # ----------------------------------------------------------------------
        print("\n[5/5] Generando Guía EPG unificada y exportando M3U...")

        # Fusionar guías EPG (Argentina + España + México + Chile)
        EPGManager.merge_and_save_epg(
            epg_sources=self.epg_sources,
            active_channels=alive_channels,
            output_xml_path=output_epg_xml,
            output_gz_path=output_epg_gz
        )

        # Referencias de EPG para la cabecera M3U
        epg_header_refs = [
            "epg.xml.gz",
            "epg.xml",
            "https://epgshare01.online/epgshare01/epg_ripper_AR1.xml.gz",
            "https://epgshare01.online/epgshare01/epg_ripper_ES1.xml.gz"
        ]

        M3UExporter.export(
            alive_channels,
            output_file,
            epg_references=epg_header_refs,
            sort_by_category=sort_by_category
        )
        print(f"✔ Lista M3U final exportada con éxito en: '{output_file}' ({len(alive_channels)} canales).")

        print("\n" + "=" * 68)
        print(" PROCESAMIENTO AUTOMATIZADO COMPLETADO EXITOSAMENTE")
        print("=" * 68)

        return {
            "total_loaded": len(all_channels),
            "alive": len(alive_channels),
            "dead": len(dead_channels),
            "categories": category_counts,
            "output_playlist": output_file,
            "output_epg_gz": output_epg_gz,
            "output_epg_xml": output_epg_xml
        }


# ==============================================================================
# CLI
# ==============================================================================

def build_cli():
    parser = argparse.ArgumentParser(
        description="Pipeline autónomo de procesamiento M3U con fusión EPG para GitHub Actions y local.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "-i", "--input",
        nargs="+",
        help="URLs remotas o archivos locales M3U.",
        default=DEFAULT_URLS
    )
    parser.add_argument(
        "-o", "--output",
        help="Ruta del archivo M3U final.",
        default=DEFAULT_OUTPUT_PLAYLIST
    )
    parser.add_argument(
        "--epg-xml",
        help="Ruta del archivo EPG XML unificado.",
        default=DEFAULT_OUTPUT_EPG_XML
    )
    parser.add_argument(
        "--epg-gz",
        help="Ruta del archivo EPG GZ comprimido.",
        default=DEFAULT_OUTPUT_EPG_GZ
    )
    parser.add_argument(
        "-c", "--config",
        help="Ruta al archivo JSON de configuración.",
        default=DEFAULT_CONFIG_FILE
    )
    parser.add_argument(
        "--dedupe-mode",
        choices=["smart", "url"],
        default="smart",
        help="Modo de deduplicación: 'smart' o 'url'."
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        help="Hilos concurrentes para verificación HTTP.",
        default=35
    )
    parser.add_argument(
        "-t", "--timeout",
        type=float,
        help="Tiempo de espera en segundos por enlace.",
        default=5.0
    )
    parser.add_argument(
        "--skip-check",
        action="store_true",
        help="Omitir verificación HTTP para procesamiento ultra rápido."
    )
    parser.add_argument(
        "--no-dedupe",
        action="store_true",
        help="Desactivar deduplicación."
    )
    parser.add_argument(
        "--no-sort",
        action="store_true",
        help="No ordenar alfabéticamente por categoría."
    )
    return parser


def main():
    parser = build_cli()
    args = parser.parse_args()

    processor = M3UProcessor(
        config_file=args.config,
        timeout=args.timeout,
        max_workers=args.workers
    )

    processor.process(
        sources=args.input,
        output_file=args.output,
        output_epg_xml=args.epg_xml,
        output_epg_gz=args.epg_gz,
        verify_links=not args.skip_check,
        deduplicate=not args.no_dedupe,
        dedupe_mode=args.dedupe_mode,
        sort_by_category=not args.no_sort
    )


if __name__ == "__main__":
    main()
