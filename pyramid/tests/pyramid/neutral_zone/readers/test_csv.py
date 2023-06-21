import numpy as np

from pathlib import Path
from pytest import fixture, raises

from pyramid.model.numeric_events import NumericEventList
from pyramid.neutral_zone.readers.csv import CsvNumericEventReader


@fixture
def fixture_path(request):
    this_file = Path(request.module.__file__)
    return Path(this_file.parent, 'fixture_files')


def test_safe_to_spam_exit(fixture_path):
    csv_file = Path(fixture_path, 'empty.csv').as_posix()
    reader = CsvNumericEventReader(csv_file)
    reader.__exit__(None, None, None)
    reader.__enter__()
    reader.__exit__(None, None, None)
    reader.__exit__(None, None, None)

    assert reader.file_stream is None


def test_empty_file(fixture_path):
    csv_file = Path(fixture_path, 'empty.csv').as_posix()
    with CsvNumericEventReader(csv_file) as reader:
        with raises(StopIteration) as exception_info:
            reader.read_next(1.0)
        assert exception_info.errisinstance(StopIteration)

    assert reader.file_stream is None


def test_csv_with_header_line(fixture_path):
    csv_file = Path(fixture_path, 'header_line.csv').as_posix()
    with CsvNumericEventReader(csv_file) as reader:
        # Consume the header line.
        assert reader.read_next(1.0) is None

        # Read 32 lines...
        for t in range(32):
            event_list = reader.read_next(1.0)
            expected_event_list = NumericEventList(np.array([[t, t + 100, t + 1000]]))
            assert event_list == expected_event_list

        # ...then be done.
        with raises(StopIteration) as exception_info:
            reader.read_next(1.0)
        assert exception_info.errisinstance(StopIteration)

    assert reader.file_stream is None


def test_csv_with_no_header_line(fixture_path):
    csv_file = Path(fixture_path, 'no_header_line.csv').as_posix()
    with CsvNumericEventReader(csv_file) as reader:
        # Read 32 lines...
        for t in range(32):
            event_list = reader.read_next(1.0)
            expected_event_list = NumericEventList(np.array([[t, t + 100, t + 1000]]))
            assert event_list == expected_event_list

        # ...then be done.
        with raises(StopIteration) as exception_info:
            reader.read_next(1.0)
        assert exception_info.errisinstance(StopIteration)

    assert reader.file_stream is None


def test_csv_skip_nonnumeric_lines(fixture_path):
    csv_file = Path(fixture_path, 'nonnumeric_lines.csv').as_posix()
    nonnumeric_lines = [1, 11, 15, 21, 28]
    with CsvNumericEventReader(csv_file) as reader:
        # Read 32 lines...
        for t in range(32):
            event_list = reader.read_next(1.0)

            if t in nonnumeric_lines:
                expected_event_list = None
            else:
                expected_event_list = NumericEventList(np.array([[t, t + 100, t + 1000]]))
            assert event_list == expected_event_list

        # ...then be done.
        with raises(StopIteration) as exception_info:
            reader.read_next(1.0)
        assert exception_info.errisinstance(StopIteration)

    assert reader.file_stream is None
