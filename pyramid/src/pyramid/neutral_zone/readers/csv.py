import csv
import logging
import numpy as np

from pyramid.model.numeric_events import NumericEventReader, NumericEventList

# Csv string event reader?
# Csv signal reader?


class CsvNumericEventReader(NumericEventReader):
    """Read numeric events from a CSV of numbers.

    Skips any lines that contain non-numeric values.
    """

    def __init__(self, csvfile: str, dialect: str = 'excel', **fmtparams) -> None:
        self.csvfile = csvfile
        self.stream = None
        self.reader = None
        self.dialect = dialect
        self.fmtparams = fmtparams

    def set_up(self) -> None:
        # Why newline='' -- https://docs.python.org/3/library/csv.html#id3
        self.stream = open(self.csvfile, mode='r', newline='')
        self.reader = csv.reader(
            self.stream,
            self.dialect,
            **self.fmtparams
        )

    def clean_up(self):
        if self.stream:
            self.stream.close()
            self.stream = None
            self.reader = None

    def read_next(self, timeout: float) -> NumericEventList:
        line_num = self.reader.line_num
        next_row = self.reader.__next__()
        try:
            numeric_row = [float(element) for element in next_row]
        except ValueError as error:
            logging.info(f"Skipping CSV {self.csvfile}, line {line_num}, with non-numeric value {error.args}: {next_row}")
            return None
        return NumericEventList(np.array(numeric_row))
