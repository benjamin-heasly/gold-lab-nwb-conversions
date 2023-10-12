from typing import Any
from pathlib import Path

import csv
import numpy as np


def parse_sample_rate(params_py: str) -> float:
    with open(params_py, "r") as f:
        for line in f:
            (name, value) = line.split("=")
            if name.strip() == "sample_rate":
                sample_rate = float(value.strip())
                return sample_rate

    raise ValueError(f"Params file {params_py} has no entry for sample_rate.")


params_py = Path("gold-phy", "params.py")
#params_py = Path("phy-data-master", "template", "params.py")

print(params_py)

sample_rate = parse_sample_rate(params_py)
print(sample_rate)

dialect = "excel"
fmtparams = {}
cluster_file_glob = "cluster_*"
cluster_file_delimiter = "\t"
cluster_id_column_name = "cluster_id"
spike_times_file_name = "spike_times.npy"
spike_clusters_file_name = "spike_clusters.npy"
numpy_memmap_mode = "r"
rows_per_read = 100

cluster_info = {}
cluster_info_files = params_py.parent.glob(cluster_file_glob)
for cluster_info_file in cluster_info_files:
    print(cluster_info_file)
    with open(cluster_info_file, mode='r', newline='') as f:
        csv_reader = csv.DictReader(f, delimiter=cluster_file_delimiter, dialect=dialect, **fmtparams)
        for row in csv_reader:
            cluster_id = row.get(cluster_id_column_name)
            info = cluster_info.get(cluster_id, {})
            info.update(row)
            cluster_info[cluster_id] = info

print(cluster_info)

spike_times_npy = Path(params_py.parent, spike_times_file_name)
spike_times = np.load(spike_times_npy, mmap_mode=numpy_memmap_mode)

spike_clusters_npy = Path(params_py.parent, spike_clusters_file_name)
spike_clusters = np.load(spike_clusters_npy, mmap_mode=numpy_memmap_mode)

row_count = spike_times.shape[0]
current_row = 0
while current_row < row_count:
    until_row = min(row_count, current_row + rows_per_read)

    times = spike_times[current_row:until_row] / sample_rate
    clusters = spike_clusters[current_row:until_row]

    # TODO: filter spikes using cluster_info -- literal filtering?  expression?

    #print(times.T)
    #print(clusters.T)

    current_row += rows_per_read
