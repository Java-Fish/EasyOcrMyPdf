"""Klartextnamen für die Sprachcodes von Tesseract.

Tesseract benennt seine Sprachpakete nach ISO 639-2/T (z. B. ``deu``, ``eng``).
Für Einsteiger ist das unverständlich, deshalb übersetzt dieses Modul die
Codes in lesbare Namen. Unbekannte Codes werden unverändert durchgereicht.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

# Sprachen, die in der Auswahl ganz oben als Vorschläge erscheinen.
FEATURED_LANGUAGES: Tuple[str, ...] = ("deu", "eng", "fra", "spa", "ita", "nld")

# Code -> (deutscher Name, englischer Name)
_LANGUAGE_NAMES: Dict[str, Tuple[str, str]] = {
    "afr": ("Afrikaans", "Afrikaans"),
    "amh": ("Amharisch", "Amharic"),
    "ara": ("Arabisch", "Arabic"),
    "asm": ("Assamesisch", "Assamese"),
    "aze": ("Aserbaidschanisch", "Azerbaijani"),
    "aze_cyrl": ("Aserbaidschanisch (kyrillisch)", "Azerbaijani (Cyrillic)"),
    "bel": ("Belarussisch", "Belarusian"),
    "ben": ("Bengalisch", "Bengali"),
    "bod": ("Tibetisch", "Tibetan"),
    "bos": ("Bosnisch", "Bosnian"),
    "bre": ("Bretonisch", "Breton"),
    "bul": ("Bulgarisch", "Bulgarian"),
    "cat": ("Katalanisch", "Catalan"),
    "ceb": ("Cebuano", "Cebuano"),
    "ces": ("Tschechisch", "Czech"),
    "chi_sim": ("Chinesisch (vereinfacht)", "Chinese (simplified)"),
    "chi_sim_vert": ("Chinesisch (vereinfacht, senkrecht)", "Chinese (simplified, vertical)"),
    "chi_tra": ("Chinesisch (traditionell)", "Chinese (traditional)"),
    "chi_tra_vert": ("Chinesisch (traditionell, senkrecht)", "Chinese (traditional, vertical)"),
    "chr": ("Cherokee", "Cherokee"),
    "cos": ("Korsisch", "Corsican"),
    "cym": ("Walisisch", "Welsh"),
    "dan": ("Dänisch", "Danish"),
    "deu": ("Deutsch", "German"),
    "deu_frak": ("Deutsch (Fraktur)", "German (Fraktur)"),
    "deu_latf": ("Deutsch (Fraktur)", "German (Fraktur)"),
    "div": ("Dhivehi", "Dhivehi"),
    "dzo": ("Dzongkha", "Dzongkha"),
    "ell": ("Griechisch", "Greek"),
    "eng": ("Englisch", "English"),
    "enm": ("Englisch (mittelalterlich)", "English (Middle)"),
    "epo": ("Esperanto", "Esperanto"),
    "equ": ("Mathematische Formeln", "Math / equations"),
    "est": ("Estnisch", "Estonian"),
    "eus": ("Baskisch", "Basque"),
    "fao": ("Färöisch", "Faroese"),
    "fas": ("Persisch", "Persian"),
    "fil": ("Filipino", "Filipino"),
    "fin": ("Finnisch", "Finnish"),
    "fra": ("Französisch", "French"),
    "frk": ("Fraktur", "Fraktur"),
    "frm": ("Französisch (mittelalterlich)", "French (Middle)"),
    "fry": ("Westfriesisch", "Western Frisian"),
    "gla": ("Schottisch-Gälisch", "Scottish Gaelic"),
    "gle": ("Irisch", "Irish"),
    "glg": ("Galicisch", "Galician"),
    "grc": ("Altgriechisch", "Ancient Greek"),
    "guj": ("Gujarati", "Gujarati"),
    "hat": ("Haitianisch", "Haitian"),
    "heb": ("Hebräisch", "Hebrew"),
    "hin": ("Hindi", "Hindi"),
    "hrv": ("Kroatisch", "Croatian"),
    "hun": ("Ungarisch", "Hungarian"),
    "hye": ("Armenisch", "Armenian"),
    "iku": ("Inuktitut", "Inuktitut"),
    "ind": ("Indonesisch", "Indonesian"),
    "isl": ("Isländisch", "Icelandic"),
    "ita": ("Italienisch", "Italian"),
    "ita_old": ("Italienisch (historisch)", "Italian (old)"),
    "jav": ("Javanisch", "Javanese"),
    "jpn": ("Japanisch", "Japanese"),
    "jpn_vert": ("Japanisch (senkrecht)", "Japanese (vertical)"),
    "kan": ("Kannada", "Kannada"),
    "kat": ("Georgisch", "Georgian"),
    "kat_old": ("Georgisch (historisch)", "Georgian (old)"),
    "kaz": ("Kasachisch", "Kazakh"),
    "khm": ("Khmer", "Khmer"),
    "kir": ("Kirgisisch", "Kyrgyz"),
    "kmr": ("Kurdisch (Kurmandschi)", "Kurdish (Kurmanji)"),
    "kor": ("Koreanisch", "Korean"),
    "kor_vert": ("Koreanisch (senkrecht)", "Korean (vertical)"),
    "lao": ("Laotisch", "Lao"),
    "lat": ("Latein", "Latin"),
    "lav": ("Lettisch", "Latvian"),
    "lit": ("Litauisch", "Lithuanian"),
    "ltz": ("Luxemburgisch", "Luxembourgish"),
    "mal": ("Malayalam", "Malayalam"),
    "mar": ("Marathi", "Marathi"),
    "mkd": ("Mazedonisch", "Macedonian"),
    "mlt": ("Maltesisch", "Maltese"),
    "mon": ("Mongolisch", "Mongolian"),
    "mri": ("Maori", "Maori"),
    "msa": ("Malaiisch", "Malay"),
    "mya": ("Birmanisch", "Burmese"),
    "nep": ("Nepalesisch", "Nepali"),
    "nld": ("Niederländisch", "Dutch"),
    "nor": ("Norwegisch", "Norwegian"),
    "oci": ("Okzitanisch", "Occitan"),
    "ori": ("Odia", "Odia"),
    "osd": ("Schriftrichtung erkennen", "Orientation & script detection"),
    "pan": ("Punjabi", "Punjabi"),
    "pol": ("Polnisch", "Polish"),
    "por": ("Portugiesisch", "Portuguese"),
    "pus": ("Paschtu", "Pashto"),
    "que": ("Quechua", "Quechua"),
    "ron": ("Rumänisch", "Romanian"),
    "rus": ("Russisch", "Russian"),
    "san": ("Sanskrit", "Sanskrit"),
    "sin": ("Singhalesisch", "Sinhala"),
    "slk": ("Slowakisch", "Slovak"),
    "slv": ("Slowenisch", "Slovenian"),
    "snd": ("Sindhi", "Sindhi"),
    "spa": ("Spanisch", "Spanish"),
    "spa_old": ("Spanisch (historisch)", "Spanish (old)"),
    "sqi": ("Albanisch", "Albanian"),
    "srp": ("Serbisch", "Serbian"),
    "srp_latn": ("Serbisch (lateinisch)", "Serbian (Latin)"),
    "sun": ("Sundanesisch", "Sundanese"),
    "swa": ("Suaheli", "Swahili"),
    "swe": ("Schwedisch", "Swedish"),
    "syr": ("Syrisch", "Syriac"),
    "tam": ("Tamil", "Tamil"),
    "tat": ("Tatarisch", "Tatar"),
    "tel": ("Telugu", "Telugu"),
    "tgk": ("Tadschikisch", "Tajik"),
    "tha": ("Thai", "Thai"),
    "tir": ("Tigrinya", "Tigrinya"),
    "ton": ("Tongaisch", "Tongan"),
    "tur": ("Türkisch", "Turkish"),
    "uig": ("Uigurisch", "Uyghur"),
    "ukr": ("Ukrainisch", "Ukrainian"),
    "urd": ("Urdu", "Urdu"),
    "uzb": ("Usbekisch", "Uzbek"),
    "uzb_cyrl": ("Usbekisch (kyrillisch)", "Uzbek (Cyrillic)"),
    "vie": ("Vietnamesisch", "Vietnamese"),
    "yid": ("Jiddisch", "Yiddish"),
    "yor": ("Yoruba", "Yoruba"),
}

# Codes, die keine echten Sprachen sind und die Auswahl nur unübersichtlich machen.
_NON_LANGUAGE_CODES = frozenset({"osd", "equ"})


def display_name(code: str, ui_language: str = "de") -> str:
    """Liefert den lesbaren Namen inklusive Code, z. B. ``Deutsch (deu)``."""
    names = _LANGUAGE_NAMES.get(code)
    if names is None:
        return code
    name = names[0] if ui_language == "de" else names[1]
    return f"{name} ({code})"


def sort_key(code: str, ui_language: str = "de") -> str:
    """Sortierschlüssel nach Klartextnamen, damit die Liste alphabetisch wirkt."""
    names = _LANGUAGE_NAMES.get(code)
    if names is None:
        return code.lower()
    return (names[0] if ui_language == "de" else names[1]).lower()


def is_selectable(code: str) -> bool:
    """``osd``/``equ`` sind Hilfsmodelle und werden nicht zur Auswahl angeboten."""
    return code not in _NON_LANGUAGE_CODES


def order_for_display(codes: List[str], ui_language: str = "de") -> List[str]:
    """Sortiert Codes: häufige Sprachen zuerst, danach alphabetisch."""
    usable = [code for code in codes if is_selectable(code)]
    featured = [code for code in FEATURED_LANGUAGES if code in usable]
    rest = sorted(
        (code for code in usable if code not in featured),
        key=lambda code: sort_key(code, ui_language),
    )
    return featured + rest
