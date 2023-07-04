from typing import Self
import logging
import csv
import numpy as np

from pyramid.model.events import NumericEventList
from pyramid.model.model import BufferData
from pyramid.neutral_zone.readers.readers import Reader


class CsvNumericEventReader(Reader):
    """Read numeric events from a CSV of numbers.

    Skips lines that contain non-numeric values.
    """

    def __init__(
        self,
        csv_file: str = None,
        results_key: str = "events",
        dialect: str = 'excel',
        **fmtparams
    ) -> None:
        self.csv_file = csv_file
        self.results_key = results_key
        self.dialect = dialect
        self.fmtparams = fmtparams

        self.file_stream = None
        self.csv_reader = None

    def __eq__(self, other: object) -> bool:
        """Compare CSV readers field-wise, to support use of this class in tests."""
        if isinstance(other, self.__class__):
            return (
                self.csv_file == other.csv_file
                and self.results_key == other.results_key
                and self.dialect == other.dialect
                and self.fmtparams == other.fmtparams
            )
        else:  # pragma: no cover
            return False

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
                self.results_key: NumericEventList(np.array([numeric_row]))
            }
        except ValueError as error:
            logging.info(f"Skipping CSV '{self.csv_file}' line {line_num} <{next_row}> because {error.args}")
            return None

    def get_initial(self) -> dict[str, BufferData]:
        try:
            # Peek at the first line of the CSV to get the column count.
            with open(self.csv_file, mode='r', newline='') as peek_stream:
                peek_reader = csv.reader(peek_stream, self.dialect, **self.fmtparams)
                first_row = peek_reader.__next__()
            column_count = len(first_row)
        except Exception:
            column_count = 2
            logging.error(f"Unable to read column count from CSV file {self.csv_file}, using default {column_count}", exc_info=True)

        return {
            self.results_key: NumericEventList(np.empty([0, column_count]))
        }
