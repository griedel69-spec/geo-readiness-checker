"""
Google-Sheets-Anbindung des GEO-Readiness-Checkers (Lead-Register).

Von der Streamlit-App getrennt, damit die Logik ohne Streamlit testbar ist.
Zugriff über den Service-Account (Render-Umgebungsvariable
GCP_SERVICE_ACCOUNT_TOML -> .streamlit/secrets.toml, Sektion
[gcp_service_account]).
"""
from __future__ import annotations

import datetime

import gspread
from google.oauth2.service_account import Credentials

SHEET_ID = "1bNBtr9w__zlPL_5XETHhewu3TZAc7qAR1wm8sRO5WVI"
SHEET_TAB = "Leads"
SHEET_HEADER = ["Datum", "Betrieb", "Ort", "E-Mail", "Website", "Typ",
                "Ampel", "Signale", "Versand"]

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_sheet(creds_dict: dict):
    creds = Credentials.from_service_account_info(creds_dict, scopes=_SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).worksheet(SHEET_TAB)


def schreibe_lead(sheet, data: dict, jetzt: datetime.datetime | None = None) -> None:
    """
    Haengt eine Lead-Zeile buendig ab Spalte A an.

    Kopfzeilen-Migration: Im Alt-Sheet stand ein manuell angelegter Kopf
    (Score-Layout), wodurch gspread neue Zeilen an den zuletzt erkannten
    Datenblock (ab Spalte G) angehaengt hat. Passt Zeile 1 nicht zum neuen
    Layout, wird der neue Kopf DARUEBER eingefuegt — alte Zeilen bleiben
    unveraendert darunter erhalten. table_range="A1" erzwingt den Anhang
    ab Spalte A.
    """
    try:
        zeile1 = sheet.row_values(1)
    except Exception:
        zeile1 = []
    if zeile1[:len(SHEET_HEADER)] != SHEET_HEADER:
        sheet.insert_row(SHEET_HEADER, index=1)

    jetzt = jetzt or datetime.datetime.now()
    sheet.append_row([
        jetzt.strftime("%d.%m.%Y %H:%M"),
        data.get("betrieb", ""),
        data.get("ort", ""),
        data.get("email", ""),
        data.get("website", ""),
        data.get("typ", ""),
        data.get("ampel", ""),
        data.get("signale", ""),
        data.get("versand", ""),
    ], table_range="A1")
