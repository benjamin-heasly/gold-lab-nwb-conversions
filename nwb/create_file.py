import uuid
from datetime import datetime
from dateutil import tz

from pynwb import NWBHDF5IO, NWBFile
from pynwb.file import Subject

# This creates a new NWB file to represent a recording session.
# It doesn't add data to the file yet!
# It just gets things started with appropriate metadata.

# From args or defaults:
nwb_file = f"./cool_cool.nwb"
nwb_identifier = str(uuid.uuid4())
zone_name = "US/Eastern"
session_start_time = datetime.now(tz.gettz(zone_name))
session_id = "cool_cool_123"
extra_metadata = {
    "session_description": "A monkey doing interesting things."
}

# Read from an "experiment.yaml":
experiment = {
    "experimenter": ["Last, First M", "Last, First Middle"],
    "experiment_description": "An experiment from the Gold Lab.",
    "institution": "University of Pennsylvania School of Medicine",
    "keywords": ["cool", "science"],
    "lab": "The Gold Lab",
    "related_publications": "DOI:10.1016/j.neuron.2016.12.011",
}
nwbfile = NWBFile(
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
    "date_of_birth": datetime(2000, 1, 1, 0, 0, 0, tzinfo=tz.gettz(zone_name)),
    "description": "A great monkey",
    "weight": "10.0 kg"
}
nwbfile.subject = Subject(**subject)

print(f"Writing NWB file: {nwb_file}")
with NWBHDF5IO(nwb_file, "w") as io:
    io.write(nwbfile)
