import codecs
import dataclasses
import io
from csv import Dialect, DictReader, register_dialect
from datetime import date, datetime, timezone
from enum import Enum, IntEnum
from typing import Annotated, Optional

import pytest
from dataclass_csv import DataclassReader, DataclassWriter, dateformat

from lsetwatch_csv.lsetwatch import (
    BellEscapedAsciiString,
    LsetAccessoryStatus,
    LsetCashbackType,
    LsetInventoryStatus,
    LsetPurchaseStatus,
    LsetStatus,
    LsetTemplate,
    LsetwatchRow,
    csv_reader,
    csv_writer,
)


@pytest.fixture
def lsetwatch_csvfile():
    # locale EN_NZ
    lines = [
        # header
        "number;version;marker;color;template;mygroup;state;purc_condition;purc_platform;purc_person;purc_date;purc_number;purc_price;purc_shipc;purc_costs;purc_items;sell_condition;sell_platform;sell_person;sell_date;sell_number;sell_price;sell_shipc;sell_costs;sell_items;vip_points_get;vip_points_sub;cashback;cashback_type;location;addition;completeness;altern_pieces;packaging;instructions;sales_value;to_sell;notes;mytags;documents;reminder_date;last_edit",
        # template: free
        "3178;1;;;;My category;2;4;TradeMe;seller;;P123456789;10;4.5;;1;;;;;;;;;1;;;;;Lager;no spares;1;100;;4;;;my notes for this set;city;Z:/Downloads/Brickset-MySets-owned.csv|Z:/Downloads/IMG_20160710_103837.jpg;30/12/2023;1702112924",
        # template: sealed
        "4531;1;;;1;;1;1;Bricklink;Some shop;06/06/2023;;437.71;216.3538;10.82;2;;;;;;;;;1;;;;;;;1;;1;1;;;;;;;1702113145",
        # template: sold
        "3221;1;;;3;;10;5;;;;;20;10;;1;4;TradeMe;Somebody;08/12/2023;P123456789;45;9.5;0.5;1;;;;;;;;;;;;;;;;;1702113042",
        # template: wishlist
        "4496;1;;;2;;;;Wunschliste;;;;;;;1;;;;;;;;;1;;;;;;;;;;;;;;;;;1702113074",
        # escape characters: quote and semicolon
        "1;1;;;;category with semicolon \a59;;;;;;;;;;;;;;;;;;;1;;;;;;;;;;;;;note with \a34quote\a34 and diacritic ā;tag with pipe \a124|tag with semicolon \a59;;;1702113511",
    ]
    content = "\r\n".join(lines)
    with io.StringIO(content) as file:
        yield file


@pytest.fixture
def lsetwatch_csvfile_observed():
    # locale EN_NZ
    lines = [
        # header
        "number;version;marker;color;template;mygroup;state;purc_condition;purc_platform;purc_person;purc_date;purc_number;purc_price;purc_shipc;purc_costs;purc_items;sell_condition;sell_platform;sell_person;sell_date;sell_number;sell_price;sell_shipc;sell_costs;sell_items;vip_points_get;vip_points_sub;cashback;cashback_type;location;addition;completeness;altern_pieces;packaging;instructions;sales_value;to_sell;notes;mytags;documents;reminder_date;last_edit",
        # escape characters: in list as exported from Lsetwatch (missing escaping?)
        "4559;1;;;;;;;;;;;;;;1;;;;;;;;;1;;;;;;;;;;;;;;tag with pipe ||tag with pipe | and semicolon ;;;;1703697286",
    ]
    content = "\r\n".join(lines)
    with io.StringIO(content) as file:
        yield file


@pytest.fixture
def lsetwatch_csvfile_locale_nz():
    # locale EN_NZ
    lines = [
        "number;version;marker;color;template;mygroup;state;purc_condition;purc_platform;purc_person;purc_date;purc_number;purc_price;purc_shipc;purc_costs;purc_items;sell_condition;sell_platform;sell_person;sell_date;sell_number;sell_price;sell_shipc;sell_costs;sell_items;vip_points_get;vip_points_sub;cashback;cashback_type;location;addition;completeness;altern_pieces;packaging;instructions;sales_value;to_sell;notes;mytags;documents;reminder_date;last_edit",
        "4531;1;;;1;;1;1;;;06/06/2023;;437.71;1.1;0.9;2;;;;;;;;;1;;;;;;;1;;1;1;;;;;;;1702113145",
    ]
    content = "\r\n".join(lines)
    with io.StringIO(content) as file:
        yield file


@pytest.fixture
def lsetwatch_csvfile_locale_de():
    # locale DE_DE
    lines = [
        "number;version;marker;color;template;mygroup;state;purc_condition;purc_platform;purc_person;purc_date;purc_number;purc_price;purc_shipc;purc_costs;purc_items;sell_condition;sell_platform;sell_person;sell_date;sell_number;sell_price;sell_shipc;sell_costs;sell_items;vip_points_get;vip_points_sub;cashback;cashback_type;location;addition;completeness;altern_pieces;packaging;instructions;sales_value;to_sell;notes;mytags;documents;reminder_date;last_edit",
        "4531;1;;;1;;1;1;;;06.06.2023;;437,71;1,1;0,9;2;;;;;;;;;1;;;;;;;1;;1;1;;;;;;;1702113145",
    ]
    content = "\r\n".join(lines)
    with io.StringIO(content) as file:
        yield file


@pytest.fixture
def temp_file():
    with io.StringIO() as file:
        yield file


@pytest.fixture
def now():
    yield datetime.now()


@pytest.mark.parametrize(
    "encoded,decoded",
    [
        ("with semicolon \a59;", "with semicolon ;;"),
        ('with \a34quote\a34 and diacritic ā"', 'with "quote" and diacritic ā"'),
        ("\a34\a59", '";'),
        ("\a124", "|"),
        ("", ""),
    ],
)
def test_bell_escaped_ascii_string_decode(encoded: str, decoded: str):
    assert codecs.decode(encoded, encoding="lsetwatch") == decoded


@pytest.mark.parametrize(
    "decoded,encoded",
    [
        ("with semicolon ;;", "with semicolon \a59\a59"),
        ('with "quote" and diacritic ā"', "with \a34quote\a34 and diacritic ā\a34"),
        ('";', "\a34\a59"),
        ("|", "\a124"),
        ("", ""),
    ],
)
def test_bell_escaped_ascii_string_encode(decoded: str, encoded: str):
    assert codecs.encode(decoded, encoding="lsetwatch") == encoded


@pytest.mark.parametrize(
    "encoded,decoded",
    [
        ("item1", ["item1"]),
        ("item1|item2", ["item1", "item2"]),
        ("item1\a124", ["item1\a124"]),
        ("item1||item3", ["item1", "", "item3"]),
        ("|", ["", ""]),
        ("", [""]),
    ],
)
def test_psv_string_decode(encoded: str, decoded: list):
    assert codecs.decode(encoded, encoding="psv") == decoded


@pytest.mark.parametrize(
    "decoded,encoded",
    [
        (["item1"], "item1"),
        (["item1", "item2"], "item1|item2"),
        (["item1\a124"], "item1\a124"),
        (
            ["item1", "", "item3"],
            "item1||item3",
        ),
        (["", ""], "|"),
        ([""], ""),
        ([], ""),
    ],
)
def test_psv_string_encode(decoded: list, encoded: str):
    assert codecs.encode(decoded, encoding="psv") == encoded


def test_read_csv_dialect_dict(lsetwatch_csvfile):
    reader = DictReader(lsetwatch_csvfile, dialect="lsetwatch")
    items = [*reader]
    assert len(items) == 5


def test_read_csv_dialect_dataclass(lsetwatch_csvfile):
    reader = csv_reader(lsetwatch_csvfile)
    items = [*reader]
    assert len(items) == 5


def test_read_locale_nz(lsetwatch_csvfile_locale_nz):
    reader = csv_reader(
        lsetwatch_csvfile_locale_nz, date_format="%d/%m/%Y", locale="en_NZ.utf8"
    )
    item: LsetwatchRow = next(reader)
    assert item.purc_date == date(2023, 6, 6)
    assert item.purc_price == 437.71
    assert item.purc_shipc == 1.1
    assert item.purc_costs == 0.9


def test_read_locale_de(lsetwatch_csvfile_locale_de):
    reader = csv_reader(
        lsetwatch_csvfile_locale_de, date_format="%d.%m.%Y", locale="de_DE.utf8"
    )
    item: LsetwatchRow = next(reader)
    assert item.purc_date == date(2023, 6, 6)
    assert item.purc_price == 437.71
    assert item.purc_shipc == 1.1
    assert item.purc_costs == 0.9


def test_read_template_free(lsetwatch_csvfile):
    reader = csv_reader(lsetwatch_csvfile)

    item: LsetwatchRow = next(filter(lambda i: i.number == "3178", reader))
    assert item is not None

    expected = LsetwatchRow(
        number="3178",
        version="1",
        marker=0,  # TODO: should be None?
        color=None,
        template=LsetTemplate.FREIE_KONFIGURATION,
        mygroup="My category",
        state=LsetStatus.GEOEFFNET,
        purc_condition=LsetPurchaseStatus.GEBRAUCHT_VOLLSTAENDIG,
        purc_platform="TradeMe",
        purc_person="seller",
        purc_date=None,
        purc_number="P123456789",
        purc_price=10,
        purc_shipc=4.5,
        purc_costs=None,
        purc_items=1,
        sell_condition=None,
        sell_platform=None,
        sell_person=None,
        sell_date=None,
        sell_number=None,
        sell_price=None,
        sell_shipc=None,
        sell_costs=None,
        sell_items=1,
        vip_points_get=None,
        vip_points_sub=None,
        cashback=None,
        cashback_type=None,
        location="Lager",
        addition="no spares",
        completeness=LsetInventoryStatus.KOMPLETT,
        altern_pieces=100,
        packaging=LsetAccessoryStatus.NICHT_VORHANDEN,
        instructions=LsetAccessoryStatus.VORHANDEN_BESCHAEDIGT,
        sales_value=None,
        to_sell=None,
        notes="my notes for this set",
        mytags=["city"],
        documents=[
            "Z:/Downloads/Brickset-MySets-owned.csv",
            "Z:/Downloads/IMG_20160710_103837.jpg",
        ],
        reminder_date=date(2023, 12, 30),
        last_edit=datetime.fromtimestamp(1702112924, timezone.utc),
    )
    assert item == expected


def test_read_template_sealed(lsetwatch_csvfile):
    reader = csv_reader(lsetwatch_csvfile)

    item: LsetwatchRow = next(filter(lambda i: i.number == "4531", reader))
    assert item is not None

    expected = LsetwatchRow(
        number="4531",
        version="1",
        marker=0,
        color=None,
        template=LsetTemplate.VERSIEGELT,
        mygroup=None,
        state=LsetStatus.VERSIEGELT,
        purc_condition=LsetPurchaseStatus.VERSIEGELT,
        purc_platform="Bricklink",
        purc_person="Some shop",
        purc_date=date(2023, 6, 6),
        purc_number=None,
        purc_price=437.71,
        purc_shipc=216.3538,
        purc_costs=10.82,
        purc_items=2,
        sell_condition=None,
        sell_platform=None,
        sell_person=None,
        sell_date=None,
        sell_number=None,
        sell_price=None,
        sell_shipc=None,
        sell_costs=None,
        sell_items=1,
        vip_points_get=None,
        vip_points_sub=None,
        cashback=None,
        cashback_type=None,
        location=None,
        addition=None,
        completeness=LsetInventoryStatus.KOMPLETT,
        altern_pieces=None,
        packaging=LsetAccessoryStatus.VORHANDEN_NEUWERTIG,
        instructions=LsetAccessoryStatus.VORHANDEN_NEUWERTIG,
        sales_value=None,
        to_sell=None,
        notes=None,
        mytags=[],
        documents=[],
        reminder_date=None,
        last_edit=datetime.fromtimestamp(1702113145, timezone.utc),
    )
    assert item == expected


def test_read_template_sold(lsetwatch_csvfile):
    reader = csv_reader(lsetwatch_csvfile)

    item: LsetwatchRow = next(filter(lambda i: i.number == "3221", reader))
    assert item is not None

    expected = LsetwatchRow(
        number="3221",
        version="1",
        marker=0,
        color=None,
        template=LsetTemplate.VERKAUFT,
        mygroup=None,
        state=LsetStatus.VERKAUFT,
        purc_condition=LsetPurchaseStatus.GEBRAUCHT_UNVOLLSTAENDIG,
        purc_platform=None,
        purc_person=None,
        purc_date=None,
        purc_number=None,
        purc_price=20.0,
        purc_shipc=10.0,
        purc_costs=None,
        purc_items=1,
        sell_condition=LsetPurchaseStatus.GEBRAUCHT_VOLLSTAENDIG,
        sell_platform="TradeMe",
        sell_person="Somebody",
        sell_date=date(2023, 12, 8),
        sell_number="P123456789",
        sell_price=45.0,
        sell_shipc=9.5,
        sell_costs=0.5,
        sell_items=1,
        vip_points_get=None,
        vip_points_sub=None,
        cashback=None,
        cashback_type=None,
        location=None,
        addition=None,
        completeness=LsetInventoryStatus.OHNE_ANGABE,  # TODO: Should be none?
        altern_pieces=None,
        packaging=LsetAccessoryStatus.NICHT_VORHANDEN,  # TODO: Should be none?
        instructions=LsetAccessoryStatus.NICHT_VORHANDEN,  # TODO: Should be none?
        sales_value=None,
        to_sell=None,
        notes=None,
        mytags=[],
        documents=[],
        reminder_date=None,
        last_edit=datetime.fromtimestamp(1702113042, timezone.utc),
    )
    assert item == expected


def test_read_template_wishlist(lsetwatch_csvfile):
    reader = csv_reader(lsetwatch_csvfile)

    item: LsetwatchRow = next(filter(lambda i: i.number == "4496", reader))
    assert item is not None

    expected = LsetwatchRow(
        number="4496",
        version="1",
        marker=0,
        color=None,
        template=LsetTemplate.WUNSCHLISTE,
        mygroup=None,
        state=None,
        purc_condition=None,
        purc_platform="Wunschliste",
        purc_person=None,
        purc_date=None,
        purc_number=None,
        purc_price=None,
        purc_shipc=None,
        purc_costs=None,
        purc_items=1,
        sell_condition=None,
        sell_platform=None,
        sell_person=None,
        sell_date=None,
        sell_number=None,
        sell_price=None,
        sell_shipc=None,
        sell_costs=None,
        sell_items=1,
        vip_points_get=None,
        vip_points_sub=None,
        cashback=None,
        cashback_type=None,
        location=None,
        addition=None,
        completeness=LsetInventoryStatus.OHNE_ANGABE,  # TODO: Should be none?
        altern_pieces=None,
        packaging=LsetAccessoryStatus.NICHT_VORHANDEN,  # TODO: Should be none?
        instructions=LsetAccessoryStatus.NICHT_VORHANDEN,  # TODO: Should be none?
        sales_value=None,
        to_sell=None,
        notes=None,
        mytags=[],
        documents=[],
        reminder_date=None,
        last_edit=datetime.fromtimestamp(1702113074, timezone.utc),
    )
    assert item == expected


def test_read_escape(lsetwatch_csvfile):
    reader = csv_reader(lsetwatch_csvfile)

    item: LsetwatchRow = next(filter(lambda i: i.number == "1", reader))
    assert item is not None

    assert item.mygroup == "category with semicolon ;"
    assert item.notes == 'note with "quote" and diacritic ā'


@pytest.mark.skip(reason="string encoding within lists not implemented yet")
def test_read_escape_list(lsetwatch_csvfile):
    reader = csv_reader(lsetwatch_csvfile)

    item: LsetwatchRow = next(filter(lambda i: i.number == "1", reader))
    assert item is not None

    assert item.mytags == [
        "tag with pipe |",
        "tag with semicolon ;",
    ]


@pytest.mark.skip(reason="bug in lsetwatch causing pipe in list not to escape")
def test_read_escape_list_observed(lsetwatch_csvfile_observed):
    reader = csv_reader(lsetwatch_csvfile_observed)

    item: LsetwatchRow = next(filter(lambda i: i.number == "4559", reader))
    assert item is not None

    assert item.mytags == [
        "tag with pipe |",
        "tag with pipe | and semicolon ;",
    ]


def test_write_header(lsetwatch_csvfile, temp_file):
    writer = csv_writer(temp_file, [])
    writer.write()

    lines_csv = lsetwatch_csvfile.getvalue().split("\r\n")
    lines = temp_file.getvalue().split("\r\n")
    assert set(lines[0].split(";")) == set(lines_csv[0].split(";"))


def test_write_item(temp_file, now):
    items = [
        LsetwatchRow(
            last_edit=now,
            number="1",
            version="1",
            mygroup="mygroup",
            mytags=["one", "two"],
            purc_date=date(2020, 1, 1),
            sell_date=date(2021, 2, 20),
            reminder_date=date(2022, 3, 10),
        )
    ]
    writer = csv_writer(temp_file, items)
    writer.write(skip_header=True)

    lines = temp_file.getvalue().split("\r\n")
    assert len(lines) == 2  # one empty line
    assert (
        lines[0]
        == f"{int(now.timestamp())};1;1;0;;0;mygroup;;;;;01/01/2020;;;;;1;;;;20/02/2021;;;;;1;;;;;;;0;0;0;;;;one|two;;10/03/2022;"
    )
    pass


def test_write_escape(temp_file, now):
    items = [
        LsetwatchRow(last_edit=now, number="1", version="1", notes='note with ";"')
    ]
    writer = csv_writer(temp_file, items)
    writer.write(skip_header=True)

    lines = temp_file.getvalue().split("\r\n")
    assert len(lines) == 2  # one empty line
    assert (
        lines[0]
        == f"{int(now.timestamp())};1;1;0;;0;;;;;;;;;;;1;;;;;;;;;1;;;;;;;0;0;0;;;note with \a34\a59\a34;;;;"
    )


def test_write_locale_nz(temp_file, now):
    items = [
        LsetwatchRow(
            last_edit=now,
            number="1",
            version="1",
            purc_date=date(2023, 6, 1),
            purc_price=437.71,
            purc_shipc=1.1,
            purc_costs=0.9,
            sell_price=437.71,
            sell_shipc=1.1,
            sell_costs=0.9,
            vip_points_get=12.33,
            vip_points_sub=21.33,
            cashback=9.3,
            sales_value=437.71,
        )
    ]
    writer = csv_writer(temp_file, items, date_format="%d/%m/%Y", locale="en_NZ.utf8")
    writer.write(skip_header=True)

    lines = temp_file.getvalue().split("\r\n")
    assert len(lines) == 2  # one empty line
    assert (
        lines[0]
        == f"{int(now.timestamp())};1;1;0;;0;;;;;;01/06/2023;;437.71;1.1;0.9;1;;;;;;437.71;1.1;0.9;1;12.33;21.33;9.3;;;;0;0;0;437.71;;;;;;"
    )


def test_write_locale_de(temp_file, now):
    items = [
        LsetwatchRow(
            last_edit=now,
            number="1",
            version="1",
            purc_date=date(2023, 6, 1),
            purc_price=437.71,
            purc_shipc=1.1,
            purc_costs=0.9,
            sell_price=437.71,
            sell_shipc=1.1,
            sell_costs=0.9,
            vip_points_get=12.33,
            vip_points_sub=21.33,
            cashback=9.3,
            sales_value=437.71,
        )
    ]
    writer = csv_writer(temp_file, items, date_format="%d.%m.%Y", locale="de_DE.utf8")
    writer.write(skip_header=True)

    lines = temp_file.getvalue().split("\r\n")
    assert len(lines) == 2  # one empty line
    assert (
        lines[0]
        == f"{int(now.timestamp())};1;1;0;;0;;;;;;01.06.2023;;437,71;1,1;0,9;1;;;;;;437,71;1,1;0,9;1;12,33;21,33;9,3;;;;0;0;0;437,71;;;;;;"
    )
