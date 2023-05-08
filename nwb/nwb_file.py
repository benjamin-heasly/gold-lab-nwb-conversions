import uuid
from datetime import datetime

from pynwb import NWBHDF5IO, NWBFile
from pynwb.file import Subject


def create(
    nwb_identifier: str = str(uuid.uuid4()),
    session_start_time: datetime = datetime.utcnow(),
    session_id: str = "cool_cool_123",
    extra_metadata: dict[str, str] = {"session_description": "A monkey doing interesting things."},
    experiment_info: str = "experiment.yaml",
    subject_info: str = "subject.yaml"
) -> NWBFile:
    """ Create a new NWB file to represent a recording session.
        This doesn't add data to the file yet.
        It just gets things started in memory with appropriate metadata.
    """

    # Read from an "experiment.yaml":
    experiment = {
        "experimenter": ["Last, First M", "Last, First Middle"],
        "experiment_description": "An experiment from the Gold Lab.",
        "institution": "University of Pennsylvania School of Medicine",
        "keywords": ["cool", "science"],
        "lab": "The Gold Lab",
        "related_publications": "DOI:10.1016/j.neuron.2016.12.011",
    }
    nwb_file = NWBFile(
        identifier=nwb_identifier,
        session_start_time=session_start_time,
        session_id=session_id,
        **experiment,
        **extra_metadata)

    # Read from a "subject.yaml":
    subject = {
        "subject_id": "MrM",
        "sex": "M",
        "species": "Macaca mulatta",
        "date_of_birth": "2000-05-08T14:00:07Z",
        "description": "A great monkey",
        "weight": "10.0 kg"
    }
    if (isinstance(subject["date_of_birth"], str)):
        subject["date_of_birth"] = datetime.fromisoformat(subject["date_of_birth"])
    nwb_file.subject = Subject(**subject)

    return nwb_file


def write(nwb_file: NWBFile, file_path: str = f"./cool_cool.nwb"):
    """ Write a working NWB file in memory, to disk at the given file_path.
    """

    print(f"Writing NWB file {nwb_file.object_id} to disk: {file_path}")
    with NWBHDF5IO(file_path, "w") as io:
        io.write(nwb_file)
