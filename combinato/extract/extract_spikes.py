import numpy as np
from .interpolate import clean, upsample, downsample, align

options = dict([('threshold_factor', 5),        # 5
                ('max_spike_duration', 0.0015), # 0.0015 (seconds)
                ('indices_per_spike', 64),      # 64
                ('index_maximum', 19),          # 19
                ('upsampling_factor', 3),       # 3
                ('denoise', True),
                ('do_filter', True)
            ])


def extract_spikes(data, times, timestep, filt):

    factor = options['upsampling_factor']
    indices_per_spike = options['indices_per_spike']
    pre_indices = options['index_maximum']
    denoise = options['denoise']
    post_indices = indices_per_spike - pre_indices

    result = []

    if denoise:
        data = filt.filter_denoise(data)

    if options['do_filter']:
        data_detect = filt.filter_detect(data)
    else:
        data_detect = data

    data_extract = None

    noise_level = np.median(np.abs(data_detect)) / .6745
    threshold = options['threshold_factor'] * noise_level
    
    # find over-threshold indices and extract spikes
    over_threshold = data_detect > threshold
    under_threshold = data_detect < -threshold

    # do pos and neg
    borders = [0, 0]
    length_okay = [0, 0]
    num_spikes = [0, 0]
    maxima = [0, 0]

    borders[0] = np.diff(over_threshold).nonzero()[0]
    borders[1] = np.diff(under_threshold).nonzero()[0]

    for i in (0, 1):
        if borders[i].shape[0] % 2:
            borders[i] = borders[i][:-1]

    # 0 is pos, 1 is neg
    for i in [0, 1]:
        borders[i] = borders[i].reshape(-1,2)
        length_okay[i] = (borders[i][:,1] - borders[i][:,0]) <= \
                         options['max_spike_duration'] / timestep
        num_spikes[i] = len(length_okay[i])


    for sign in [0, 1]:
        if num_spikes[sign] == 0:
            result.append((np.zeros((0, indices_per_spike)), np.zeros(0)))
            continue

        borders[sign] = borders[sign][length_okay[sign]]

        if sign == 1:
            detect_func = np.argmin
        else:
            detect_func = np.argmax
        maxima = [detect_func(data_detect[range(borders[sign][i,0],
                                borders[sign][i,1])])
                        + borders[sign][i,0]
                        for i in range(borders[sign].shape[0])]

        if len(maxima) <= 3:
            result.append((np.zeros((0, indices_per_spike)), np.zeros(0)))
            continue

        maxima = np.array(maxima[1:-2])
        print((np.diff(maxima) < 64).sum())
        # make sure maxima are far enough from border of data
        mindex = (maxima >= pre_indices + 5) & (maxima <= len(data) - post_indices - 5)
        print('Shortening maxima list from {} to {}'.format(len(maxima), mindex.sum()))
        maxima = maxima[mindex]
        if data_extract is None:
            if options['do_filter']:
                data_extract = filt.filter_extract(data)
            else:
                data_extract = data

        extract_indices = [
            range(maxima[i] - pre_indices - 5, maxima[i] + post_indices + 5)
            for i in range(len(maxima))]

        spikes = np.zeros((len(extract_indices), indices_per_spike + 10))

        for i, spike in enumerate(extract_indices):
            spikes[i] = data_extract[extract_indices[i]]

        if sign == 1:
            spikes *= -1

        spikes = upsample(spikes, factor)

        spikes, index_maximum = align(spikes,
                                  (pre_indices + 5) * factor,
                                  factor,
                                  factor)
        _, removed_indices = clean(spikes, index_maximum)

        # this is not optimal, but the error is less than .5 ms in use cases
        timestamps = times[maxima]
        spikes, new_length = downsample(spikes, index_maximum, factor, pre_indices, indices_per_spike)

        if sign == 1:
            spikes *= -1

        result.append((spikes, timestamps))
    result.append([(times[0], times[-1], threshold)])

    return result
