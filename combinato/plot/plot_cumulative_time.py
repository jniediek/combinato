# JN 2015-10-03 refactor

"""
cumulative spike time plot
"""

import numpy as np
TEXT_SIZE = 'small'
YLIM = (-200, 200)


def spike_cumulative(plot, times, special):
    """
    draw cumulative spike line
    """
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
              np.linspace(YLIM[0], YLIM[1], len(times)), 'm', lw=1, alpha=.7)
    xlim = plot.get_xlim()
    plot.text(xlim[1], YLIM[1], dur_str, ha='right', va='top', size=TEXT_SIZE)
    if special:
        nspk_str = '{} spk '.format(len(times))
        plot.text(xlim[1], YLIM[0], nspk_str, ha='right',
                  va='bottom', size=TEXT_SIZE)
    plot.set_xticklabels([])
    plot.set_xticks([])
