"""
Exportación CSV de los reportes: separador ';', coma decimal y BOM, para que
Excel en español lo abra bien.

Seguridad: un texto que empiece por = + - @ (por ejemplo, el nombre de un
producto escrito por un usuario) se prefija con ' para que Excel no lo
ejecute como fórmula (inyección CSV).
"""
import csv
import io
import re

from django.http import HttpResponse

NUMBER = re.compile(r'^-?\d+(\.\d+)?$')
FORMULA_START = ('=', '+', '-', '@', '\t', '\r')


def cell(value) -> str:
    if value is None:
        return ''
    text = str(value)
    if isinstance(value, (int, float)) or NUMBER.match(text):
        return text.replace('.', ',')
    return "'" + text if text.startswith(FORMULA_START) else text


def csv_response(filename: str, columns: list[tuple[str, str]], rows: list[dict]) -> HttpResponse:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=';')
    writer.writerow([label for _, label in columns])
    for row in rows:
        writer.writerow([cell(row.get(key)) for key, _ in columns])
    response = HttpResponse('﻿' + buffer.getvalue(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
    return response
