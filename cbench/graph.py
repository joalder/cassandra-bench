"""
    Simple plotter for YCSB statistics

    author: Jonas Alder

"""
from collections import OrderedDict
from matplotlib import pyplot as plt
import re
import os.path
import logging
from . import settings

types = ['READ', 'INSERT', 'UPDATE', 'SCAN', 'READ-MODIFY-WRITE']
colors = ['red', 'green', 'blue', 'orange']

# measurements = ['avg', 'lat90', 'lat99']
legend_mapping = {'avg': "average",
                  'lat99': "99%-til"}
markers = ['x', 'o', '*', 'p']

log = logging.getLogger('')


def extract_base_stats(line):
    match = re.search(
        r'(?P<time>\d{2}:\d{2}:\d{2}:\d{3}) (?P<time_passed>\d+) sec: (?P<ops>\d+) operations; (?P<ops_sec>\d+(?:\.\d+)?)',
        line)
    if match:
        return match.groupdict()


def extract_latencies(line, type):
    pattern = r'\[{0}: Count=\d+, Max=(?P<max>\d+), Min=(?P<min>\d+), Avg=(?P<avg>[\d\.]+), 90=(?P<lat90>\d+), 99=(?P<lat99>\d+), 99\.9=(?P<lat999>\d+), 99\.99=(?P<lat9999>\d+)\]'.format(
        type)
    match = re.search(pattern, line)
    if match:
        stats = match.groupdict()
        stats['type'] = type
        return stats


def plot(test_name, granularity=10, measurements=None):
    if not measurements:
        measurements = settings.DEFAULT_MEASUREMENTS
    file_name = os.path.join(os.path.abspath(settings.RESULT_DIR), test_name, "ycsb_0.log")

    if not os.path.isfile(file_name):
        log.error("Could not find a log in path '{0}'".format(file_name))

    plt.style.use("ggplot")

    fig, ax1 = plt.subplots()
    ax2 = ax1.twinx()

    labels = OrderedDict()

    with open(file_name) as fh:
        for line in fh.readlines():
            if not line.startswith(test_name):
                continue
            data_point = extract_base_stats(line)
            if not data_point:
                print('WARNING: Could not match base data_point on line "{0}"'.format(line))
                continue
            if int(data_point['time_passed']) % granularity != 0:
                continue

            data_point['latencies'] = []

            scatter = ax1.scatter(data_point['time_passed'], data_point['ops_sec'], marker='s', color="black")
            labels["Ops/s"] = scatter
            for type, color in zip(types, colors):
                latency_data = extract_latencies(line, type)
                if not latency_data:
                    continue
                for lat_type, marker in zip(measurements, markers):
                    # Plot latency and correct us to ms for easier readability
                    scatter = ax2.scatter(data_point['time_passed'], float(latency_data[lat_type]) / 1000,
                                          marker=marker, color=color)
                    labels[type + " " + legend_mapping[lat_type] if lat_type in legend_mapping else lat_type] = scatter

    ax1.set_ylabel("Ops/s")
    ax1.set_xlabel("Seconds")
    ax1.set_xlim(xmin=0)
    ax1.set_ylim(ymin=0)
    ax2.set_ylabel("Latency (ms)")
    ax2.set_ylim(ymin=0)
    # Fix grid alignment
    # ax2.set_yticks(np.linspace(ax2.get_yticks()[0],ax2.get_yticks()[-1],len(ax1.get_yticks())))
    # or just turn of grid on one axis
    ax2.grid(None)
    plt.legend(labels.values(), labels.keys(), scatterpoints=1, loc="best", bbox_to_anchor=(1.0, 0.65))
    plt.savefig(os.path.join(os.path.dirname(file_name), test_name + ".png"))
    plt.show()


if __name__ == "__main__":
    name = "Reduce_READ_6_vs_m4.2xlarge_100"
    plot(name, 30)
