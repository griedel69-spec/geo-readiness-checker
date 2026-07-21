"""Tests für das Lead-Register (sheets.py) — mit Fake-Worksheet, ohne Google."""
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sheets import SHEET_HEADER, schreibe_lead   # noqa: E402


class FakeSheet:
    def __init__(self, zeile1):
        self.zeile1 = zeile1
        self.inserted = []
        self.appended = []

    def row_values(self, idx):
        assert idx == 1
        return self.zeile1

    def insert_row(self, values, index):
        self.inserted.append((values, index))

    def append_row(self, values, table_range=None):
        self.appended.append((values, table_range))


LEAD = {"betrieb": "Hotel Teststern", "ort": "Zell am See", "email": "x@example.com",
        "website": "https://example.at", "typ": "Hotel",
        "ampel": "GELB", "signale": "S1 GRÜN | S2 GELB | S3 GRÜN", "versand": "versendet"}


def test_alt_kopf_wird_migriert_und_ab_spalte_a_geschrieben():
    # Alt-Sheet: manuell angelegter Kopf mit Score-Layout
    sheet = FakeSheet(["Datum", "Betrieb", "Ort / Region", "Website", "Score (0-50)"])
    schreibe_lead(sheet, LEAD, jetzt=datetime.datetime(2026, 7, 21, 12, 0))
    assert sheet.inserted == [(SHEET_HEADER, 1)]
    (values, table_range), = sheet.appended
    assert table_range == "A1"
    assert values[0] == "21.07.2026 12:00"
    assert values[1:] == ["Hotel Teststern", "Zell am See", "x@example.com",
                          "https://example.at", "Hotel", "GELB",
                          "S1 GRÜN | S2 GELB | S3 GRÜN", "versendet"]


def test_neuer_kopf_wird_nicht_doppelt_eingefuegt():
    sheet = FakeSheet(list(SHEET_HEADER))
    schreibe_lead(sheet, LEAD)
    assert sheet.inserted == []
    assert len(sheet.appended) == 1


def test_leeres_sheet_bekommt_kopf():
    sheet = FakeSheet([])
    schreibe_lead(sheet, LEAD)
    assert sheet.inserted == [(SHEET_HEADER, 1)]
