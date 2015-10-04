# JN 2015-10-03 refactor

"""
cumulative spike time plot
"""

import numpy as np
TEXT_SIZE = 'small'


def spike_cumulative(plot, times, special, ylim=None, text=True,
                     lw=1, alpha=.7):
    """
    draw cumulative spike line
    """
    if ylim is None:
        ylim = (-200, 200)

    duration = (times[-1] - times[0])/1000  # in sec

    if duration < 60:
        dur_str = '{:.0f} s'.format(duration)
    else:
        duration /= 60  # in min
        if duration < 60:
            dur_str = '{:.0f} min'.format(duration)
        else:
            duration /= 60  # in h
            dur_str = '{:.0f} h'.format(duration)

    plot.plot(times,
              np.linspace(ylim[0], ylim[1], len(times)), 'm',
              lw=lw, alpha=alpha)

    xlim = plot.get_xlim()
    if text:
        plot.text(xlim[1], ylim[1], dur_str, ha='right',
                  va='top', size=TEXT_SIZE)
    if special:
        nspk_str = '{} spk '.format(len(times))
        plot.text(xlim[1], ylim[0], nspk_str, ha='right',
                  va='bottom', size=TEXT_SIZE)
    plot.set_xticklabels([])
    plot.set_xticks([])
