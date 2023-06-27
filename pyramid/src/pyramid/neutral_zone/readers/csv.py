from typing import Self
import logging
import csv
import numpy as np

from pyramid.neutral_zone.readers.readers import Reader
from pyramid.model.numeric_events import NumericEventList


class CsvNumericEventReader(Reader):
    """Read numeric events from a CSV of numbers.

    Skips lines that contain non-numeric values.
    """

    def __init__(self, csv_file: str, results_name: str = "events", dialect: str = 'excel', **fmtparams) -> None:
        self.csv_file = csv_file
        self.results_name = results_name
        self.dialect = dialect
        self.fmtparams = fmtparams

        self.file_stream = None
        self.csv_reader = None

    def __enter__(self) -> Self:
        # See https://docs.python.org/3/library/csv.html#id3 for why this has newline=''
        self.file_stream = open(self.csv_file, mode='r', newline='')
        self.csv_reader = csv.reader(self.file_stream, self.dialect, **self.fmtparams)
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self.file_stream:
            self.file_stream.close()
            self.file_stream = None
        self.csv_reader = None

    def read_next(self) -> dict[str, NumericEventList]:
        line_num = self.csv_reader.line_num
        next_row = self.csv_reader.__next__()
        try:
            numeric_row = [float(element) for element in next_row]
            return {
                self.results_name: NumericEventList(np.array([numeric_row]))
            }
        except ValueError as error:
            logging.info(f"Skipping CSV '{self.csv_file}' line {line_num} <{next_row}> because {error.args}")
            return None
