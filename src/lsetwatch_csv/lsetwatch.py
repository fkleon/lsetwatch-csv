import codecs
import collections
import csv
import dataclasses
import locale
import re
from datetime import date, datetime, timezone
from enum import IntEnum
from typing import Annotated, Optional

from dataclass_csv import DataclassReader, DataclassWriter, dateformat
from pydantic import Field

DEFAULT_LSET_DATE_FORMAT = "%d/%m/%Y"
DEFAULT_LSET_LOCALE = (
    locale.getlocale()
)  # e.g. ("en_US", "UTF-8") or ("de_DE", "UTF-8")

LSET_STRING_ENCODING = "lsetwatch"
LSET_LIST_ENCODING = "psv"
LSET_CSV_DIALECT = "lsetwatch"


# Custom encodings
class BellEscapedAsciiStringCodec(codecs.Codec):
    # str encoding: bell-escaped ascii characters
    ascii_chars_decode = re.compile(r"(\a)(\d{1,3})")
    ascii_chars_encode = re.compile(r'[;"|]')
    name = LSET_STRING_ENCODING

    def encode(self, input: str, errors="strict") -> str:
        encoded_string = re.sub(
            self.ascii_chars_encode, lambda m: f"\a{ord(m.group(0))}", input
        )
        return (encoded_string, len(input))

    def decode(self, input: str, errors="strict") -> str:
        decoded_string = re.sub(
            self.ascii_chars_decode, lambda m: chr(int(m.group(2))), input
        )
        return (decoded_string, len(input))


class PipeSeparatedListCodec(codecs.Codec):
    # list encoding: pipe-separated string
    separator_char = "|"
    name = LSET_LIST_ENCODING

    def encode(self, input: list, errors="strict") -> str:
        encoded_obj = self.separator_char.join(input)
        return (encoded_obj, len(input))

    def decode(self, input: str, errors="strict") -> list:
        decoded_obj = input.split(self.separator_char)
        return (decoded_obj, len(input))


# Custom CSV dialect
class LsetWatchDialect(csv.Dialect):
    """Describe the usual properties of Lsetwatch-generated CSV files."""

    delimiter = ";"
    doublequote = False
    escapechar = None
    lineterminator = "\r\n"
    quoting = csv.QUOTE_NONE
    skipinitialspace = False
    strict = True


# Custom field types
class UnixTimestampString(int):
    def __new__(cls, val: str):
        return datetime.fromtimestamp(int(val), timezone.utc)


class BellEscapedAsciiString(str):
    def __new__(cls, string):
        return super().__new__(cls, codecs.decode(string, LSET_STRING_ENCODING))

    def __str__(self):
        return codecs.encode(self, LSET_STRING_ENCODING)


class PipeSeparatedList(collections.UserList[str]):
    def __init__(self, input: str | list | None = None):
        data = (
            codecs.decode(input, LSET_LIST_ENCODING)
            if isinstance(input, str)
            else input
        )
        super().__init__(data)

    def __str__(self):
        return codecs.encode(self, LSET_LIST_ENCODING)


# Model classes
class LsetTemplate(IntEnum):
    """
    http://lebostein.de/lsetwatch/faq_de.html#SV1
    """

    FREIE_KONFIGURATION = 0  # Freie Konfiguration
    VERSIEGELT = 1  # Versiegelt
    WUNSCHLISTE = 2  # Wunschliste
    VERKAUFT = 3  # Verkauft
    VERSCHENKT = 4  # Verschenkt
    VERLOREN = 5  # Verloren


class LsetStatus(IntEnum):
    """
    http://lebostein.de/lsetwatch/faq_de.html#SV3
    """

    OHNE_ANGABE = 0  # Ohne Angabe
    VERSIEGELT = 1  # Versiegelt
    GEOEFFNET = 2  # Geöffnet
    IM_BAU = 3  # Im Bau
    ZUSAMMENGEBAUT = 4  # Zusammengebaut
    EINZELTEILE_SET = 5  # Einzelteile, als Set
    EINZELTEILE_VERMISCHT = 6  # Einzelteile, vermischt
    EINZELTEILE_VERKAUF = 7  # Einzelteile, zum Verkauf
    ARCHIVIERT = 8  # Verpackt / Archiviert
    VERBORGT = 9  # Verborgt
    VERKAUFT = 10  # Verkauft
    VERSCHENKT = 11  # Verschenkt
    VERLOREN = 12  # Verloren


class LsetPurchaseStatus(IntEnum):
    """
    http://lebostein.de/lsetwatch/faq_de.html#SV2
    """

    OHNE_ANGABE = 0  # Ohne Angabe
    VERSIEGELT = 1  # Versiegelt
    NEU_VOLLSTAENDIG = 2  # Neu, vollständig
    NEU_UNVOLLSTAENDIG = 3  # Neu, unvollständig
    GEBRAUCHT_VOLLSTAENDIG = 4  # Gebraucht, vollständig
    GEBRAUCHT_UNVOLLSTAENDIG = 5  # Gebraucht, unvollständig


class LsetInventoryStatus(IntEnum):
    """
    http://lebostein.de/lsetwatch/faq_de.html#SV4
    """

    OHNE_ANGABE = 0  # Ohne Angabe
    KOMPLETT = 1  # Komplett
    UNVOLLSTAENDIG = 2  # Unvollständig
    OHNE_MINIFIGS = 3  # Ohne Minifigs
    NUR_MINIFIGS = 4  # Nur Minifigs


class LsetAccessoryStatus(IntEnum):
    """
    http://lebostein.de/lsetwatch/faq_de.html#SV5
    """

    NICHT_VORHANDEN = 0  # nicht vorhanden
    VORHANDEN_NEUWERTIG = 1  # vorhanden (neuwertig)
    VORHANDEN_NORMAL = 2  # vorhanden (normale Gebrauchsspuren)
    VORHANDEN_LEICHT_BESCHAEDIGT = 3  # vorhanden (leicht beschädigt)
    VORHANDEN_BESCHAEDIGT = 4  # vorhanden (beschädigt)
    UNVOLLSTAENDIG = 5  # unvollständig


class LsetCashbackType(IntEnum):
    PROZENT = 0  # Prozent vom Kaufpreis
    WAEHRUNG = 1  # Als Währungsbetrag
    PAYBACK = 2  # In Payback-Punkten


@dataclasses.dataclass
@dateformat(DEFAULT_LSET_DATE_FORMAT)
class LsetwatchRow:
    """
    Lsetwatch CSV format, documented here: http://lebostein.de/lsetwatch/faq_de.html#IEM
    """

    last_edit: UnixTimestampString  # Zeitstempel der letzten Änderung (Datum/Uhrzeit im Unixzeit-Standard)
    number: str  # Setnummer ohne Set-Version
    version: str  # Set-Version
    marker: int = 0  # Nummer des Icons (Zahl zwischen 0 und 31, 0 entspricht ohne)
    # marker = Annotated[int, Field(ge=0, le=31)]
    color: Optional[
        str
    ] = None  # Markierungsfarbe des Sets (als Hex-Farbcode, z.B. #cc0022)
    template: Optional[
        LsetTemplate
    ] = LsetTemplate.FREIE_KONFIGURATION  # Verwendete Vorlage (Zahl zwischen 0 und 5)
    mygroup: Optional[BellEscapedAsciiString] = None  # Eigene Kategorie
    state: Optional[LsetStatus] = None  # Status des Sets (Zahl zwischen 0 und 12)
    purc_condition: Optional[
        LsetPurchaseStatus
    ] = None  # Zustand bei Kauf (Zahl zwischen 0 und 5)
    purc_platform: Optional[str] = None  # Kaufplattform
    purc_person: Optional[str] = None  # Verkäufer
    purc_date: Optional[
        date
    ] = None  # Kaufdatum (formatiert je nach Einstellung, z.B. 24.12.2021)
    purc_number: Optional[str] = None  # Bestellnummer
    purc_price: Optional[float] = None  # Kaufpreis (Dezimalzahl ohne Währungssymbol)
    purc_shipc: Optional[
        float
    ] = None  # Versandkosten (Dezimalzahl ohne Währungssymbol)
    purc_costs: Optional[float] = None  # Zusatzkosten (Dezimalzahl ohne Währungssymbol)
    purc_items: Optional[
        int
    ] = 1  # Anzahl gekaufter Sets für Aufteilung der Versand- und Zusatzkosten (mindestens 1 oder größer)
    sell_condition: Optional[
        LsetPurchaseStatus
    ] = None  # Zustand bei Verkauf (Zahl zwischen 0 und 5)
    sell_platform: Optional[str] = None  # Verkaufsplattform
    sell_person: Optional[str] = None  # Käufer
    sell_date: Optional[
        date
    ] = None  # Verkaufsdatum (formatiert je nach Einstellung, z.B. 24.12.2021)
    sell_number: Optional[str] = None  # Transaktionsnummer
    sell_price: Optional[
        float
    ] = None  # Verkaufspreis (Dezimalzahl ohne Währungssymbol)
    sell_shipc: Optional[
        float
    ] = None  # Versendekosten (Dezimalzahl ohne Währungssymbol)
    sell_costs: Optional[float] = None  # Aufwendungen (Dezimalzahl ohne Währungssymbol)
    sell_items: Optional[
        int
    ] = 1  # Anzahl verkaufter Sets für Aufteilung der Aufwendungen (mindestens 1 oder größer)
    vip_points_get: Optional[float] = None  # VIP-Punkte erhalten (Dezimalzahl)
    vip_points_sub: Optional[float] = None  # VIP-Punkte eingelöst (Dezimalzahl)
    cashback: Optional[
        float
    ] = None  # Cashback-Betrag (Dezimalzahl ohne Währungssymbol)
    cashback_type: Optional[
        LsetCashbackType
    ] = None  # Cashback-Typ (0 = Prozent vom Kaufpreis, 1 = Als Währungsbetrag, 2 = In Payback-Punkten)
    location: Optional[str] = None  # Aufbewahrungsort
    addition: Optional[str] = None  # Zusatzinfo
    completeness: Optional[
        LsetInventoryStatus
    ] = LsetInventoryStatus.OHNE_ANGABE  # Inventar-Status (Zahl zwischen 0 und 4)
    packaging: Optional[
        LsetAccessoryStatus
    ] = (
        LsetAccessoryStatus.NICHT_VORHANDEN
    )  # Zustand der Verpackung (Zahl zwischen 0 und 5)
    instructions: Optional[
        LsetAccessoryStatus
    ] = (
        LsetAccessoryStatus.NICHT_VORHANDEN
    )  # Zustand der Anleitung (Zahl zwischen 0 und 5)
    sales_value: Optional[
        float
    ] = None  # Verkaufspreis (Dezimalzahl ohne Währungssymbol)
    to_sell: Optional[bool] = None  # Verkauf geplant (0 = Nein, 1 = Ja)
    notes: Optional[BellEscapedAsciiString] = None  # Notizen
    mytags: PipeSeparatedList = dataclasses.field(default_factory=list)
    # Eigene Tags getrennt durch senkrechten Strich |
    documents: PipeSeparatedList = dataclasses.field(default_factory=list)
    # Pfadangaben verlinkter Dokumente getrennt durch senkrechten Strich | (Pfadtrenner: "/")
    reminder_date: Optional[
        date
    ] = None  # Erinnerungsdatum (formatiert je nach Einstellung, z.B. 24.12.2021)
    altern_pieces: Optional[int] = None  # Teilezahl ueberschreiben?


def csv_reader(csvfile):
    reader = DataclassReader(csvfile, LsetwatchRow, dialect=LSET_CSV_DIALECT)

    # unix timestamp
    # reader.type_hints["last_edit"] = lambda s: datetime.utcfromtimestamp(int(s))

    # pipe-separated string lists
    for field in ["mytags", "documents"]:
        # TODO: string encoding within lists
        pass

    # int enums
    for field in [
        "template",
        "state",
        "purc_condition",
        "sell_condition",
        "cashback_type",
        "completeness",
        "packaging",
        "instructions",
    ]:
        reader.type_hints[field] = int

    # TODO: locale support for values
    # reader.type_hints["purc_shipc"] = lambda v: locale.atof
    return reader


def csv_writer(csvfile, data):
    def encode_string(string: str | None) -> str | None:
        return (
            codecs.encode(string, LSET_STRING_ENCODING) if string is not None else None
        )

    def encode_list(list: list | None) -> list | None:
        return codecs.encode(list, LSET_LIST_ENCODING) if list is not None else None

    def encode_date(date: date | None) -> str | None:
        format_string = (
            LsetwatchRow.__dateformat__
            if LsetwatchRow.__dateformat__ is not None
            else DEFAULT_LSET_DATE_FORMAT
        )
        return date.strftime(format_string) if date is not None else None

    def encode_item(item: LsetwatchRow) -> LsetwatchRow:
        return dataclasses.replace(
            item,
            last_edit=datetime.timestamp(item.last_edit),
            mygroup=encode_string(item.mygroup),
            notes=encode_string(item.notes),
            mytags=encode_list(item.mytags),
            documents=encode_list(item.documents),
            purc_date=encode_date(item.purc_date),
            sell_date=encode_date(item.sell_date),
            reminder_date=encode_date(item.reminder_date),
        )

    encoded_data = [encode_item(i) for i in data]

    writer = DataclassWriter(
        csvfile, encoded_data, LsetwatchRow, dialect=LSET_CSV_DIALECT
    )
    return writer


# Register custom CSV dialect
csv.register_dialect(LSET_CSV_DIALECT, LsetWatchDialect)


# Register custom encodings
bell_codec = BellEscapedAsciiStringCodec()
bell_codec_info = codecs.CodecInfo(
    bell_codec.encode,
    bell_codec.decode,
    name=bell_codec.name,
)

psv_codec = PipeSeparatedListCodec()
psv_codec_info = codecs.CodecInfo(
    psv_codec.encode,
    psv_codec.decode,
    name=psv_codec.name,
)
codecs.register(
    lambda encoding: bell_codec_info if encoding == bell_codec.name else None
)
codecs.register(lambda encoding: psv_codec_info if encoding == psv_codec.name else None)
