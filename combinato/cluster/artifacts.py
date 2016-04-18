# JN 2015-01-13
# refactoring artifact calculation

"""
this module contains functions that identify
artifact clusters based on the spike wave forms
"""

from __future__ import print_function, division, absolute_import
import numpy as np
from .. import options, artifact_criteria

CRIT = artifact_criteria
TOLERANCE = 10


def find_maxima_ratio(data, tolerance):
    """
    finds number of peaks and ratio of highest peaks
    make sure data is a positive spike
    data: mean spike
    """

    up = (data[1:] > data[:-1]).nonzero()[0] + 1
    down = (data[:-1] > data[1:]).nonzero()[0]
    peaks = np.intersect1d(up, down)
    peaks = np.append(peaks, len(data))

    # exclude nearby peaks
    idx = np.diff(peaks) >= tolerance
    num = idx.sum()

    if num > 1:
        vals = np.sort(data[peaks[idx.nonzero()[0]]])
        ratio = np.abs(vals[-1]/vals[-2])
    else:
        ratio = np.inf

    return num, ratio


def max_min_ratio(data):
    """
    ratio of maximum and minimum. data: mean spike
    """
    return np.abs(data.max()/data.min())


def std_err_mean(data):
    """
    calculates deviation from mean. data: all spikes
    """
    return data.std(0).mean()/np.sqrt(data.shape[0])


def peak_to_peak(data):
    """
    peak to peak ratio in second half. data: mean spike
    """
    cut = int(data.shape[0]/2)
    return (data[cut:] - data[0]).ptp()/data.max()


def artifact_score(data):
    """
    runs all of the above tests
    """
    # could use a list of functions, but not really necessary
    mean = data.mean(0)

    num_peaks, peak_ratio = find_maxima_ratio(mean, TOLERANCE)
    ratio = max_min_ratio(mean)
    std_err = std_err_mean(data)
    ptp = peak_to_peak(mean)

    score = 0
    reasons = []

    if num_peaks > CRIT['maxima']:
        score += 1
        reasons.append('maxima')

    if peak_ratio < CRIT['maxima_1_2_ratio']:
        score += 1
        reasons.append('maxima_1_2_ratio')

    if ratio < CRIT['max_min_ratio']:
        score += 1
        reasons.append('max_min_ratio')

    if std_err > CRIT['sem']:
        score += 1
        reasons.append('sem')

    if ptp > CRIT['ptp']:
        score += 1
        reasons.append('ptp')

    # return mean for convenience
    return score, reasons, mean


def find_artifacts(spikes, sorted_idx, class_ids, invert=False):
    """
    identifies artifacts
    """
    artifact_idx = np.zeros(spikes.shape[0], np.uint8)
    artifact_ids = []

    for class_id in class_ids:
        if class_id == 0:
            continue
        class_idx = sorted_idx == class_id
        class_spikes = spikes[class_idx]
        if invert:
            class_spikes = -class_spikes
        score, reasons, _ = artifact_score(class_spikes)
        if options['Debug']:
            print(class_id, score, reasons)
        artifact_idx[class_idx] = score
        if score:
            artifact_ids.append(class_id)

    return artifact_idx, artifact_ids


def testit():
    """
    usual tests
    """
    data = np.array([[0, 1, 14, 5, 5, 5, 5, 20, 30, 0, 11, 0],
                     [-1, 3, 12, 3, 4, 7, 7, 20, 30, 0, 11, 1]], float)

    print(artifact_score(data))
