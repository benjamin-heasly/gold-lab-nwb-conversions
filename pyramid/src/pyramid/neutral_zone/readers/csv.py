from typing import Self
import logging
import csv
import numpy as np

from pyramid.model.numeric_events import NumericEventReader, NumericEventList

# Csv string event reader?
# Csv signal reader?


class CsvNumericEventReader(NumericEventReader):
    """Read numeric events from a CSV of numbers.

    Skips lines that contain non-numeric values.
    """

    def __init__(self, csv_file: str, dialect: str = 'excel', **fmtparams) -> None:
        self.csv_file = csv_file
        self.dialect = dialect
        self.fmtparams = fmtparams

        self.file_stream = None
        self.reader = None

    def __enter__(self) -> Self:
        # See https://docs.python.org/3/library/csv.html#id3 for why this has newline=''
        self.file_stream = open(self.csv_file, mode='r', newline='')
        self.reader = csv.reader(self.file_stream, self.dialect, **self.fmtparams)
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self.file_stream:
            self.file_stream.close()
            self.file_stream = None
        self.reader = None

    def read_next(self, timeout: float) -> NumericEventList:
        line_num = self.reader.line_num
        next_row = self.reader.__next__()
        try:
            numeric_row = [float(element) for element in next_row]
        except ValueError as error:
            logging.info(f"Skipping CSV {self.csv_file}, line {line_num}, with non-numeric value {error.args}: {next_row}")
            return None
        return NumericEventList(np.array([numeric_row]))
