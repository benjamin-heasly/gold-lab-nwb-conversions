import uuid
import datetime

from pynwb import NWBHDF5IO, NWBFile
from pynwb.file import Subject


def create(
    experiment_info: dict[str, str],
    subject_info: dict[str, str],
    session_id: str,
    nwb_identifier: str = str(uuid.uuid4()),
    session_start_time: datetime = datetime.datetime.now(datetime.timezone.utc),
    session_description: str = None
) -> NWBFile:
    """ Create a new NWB file to represent a recording session.
        This doesn't add data to the file yet.
        It just gets things started in memory with appropriate metadata.
    """

    nwb_file = NWBFile(
        identifier=nwb_identifier,
        session_start_time=session_start_time,
        session_id=session_id,
        session_description=session_description,
        **experiment_info
    )

    if (isinstance(subject_info["date_of_birth"], str)):
        subject_info["date_of_birth"] = datetime.fromisoformat(subject_info["date_of_birth"])
    nwb_file.subject = Subject(**subject_info)

    return nwb_file


def write(nwb_file: NWBFile, file_path: str = f"./cool_cool.nwb"):
    """ Write a working NWB file in memory, to disk at the given file_path.
    """

    print(f"Writing NWB file {nwb_file.object_id} to disk: {file_path}")
    with NWBHDF5IO(file_path, "w") as io:
        io.write(nwb_file)
