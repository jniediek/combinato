from numpy import zeros, arange
from scipy.interpolate import splmake, spleval

def upsample(data, factor):
    """
    upsample array of data by a given factor using cubic splines
    array.shape is assumed to be (num_events, num_values_per_event)
    """


    # vpe is values per event
    num_m, num_vpe = data.shape
    # new values appear only between old values, hence the "-1"
    up_num_vpe = (num_vpe - 1) * factor + 1
    axis = arange(0, up_num_vpe, factor) 
    up_axis = arange(up_num_vpe)
#   up_data = zeros((num_m, up_num_vpe))
#   for i in xrange(num_m):
#       up_data[i] = spline(axis, data[i], up_axis)
    splines = splmake(axis, data.T)
    up_data = spleval(splines, up_axis)

    return up_data.T

def align(data, center, low, high):
    """
    realign data to common maximum
    low and high define region where maxima are looked for
    """
    width = 5
    index_max = data[:,center-width*low:center+width*high].argmax(1) + center - width*low
    num_e, num_vpe = data.shape
    aligned_data = zeros((num_e, num_vpe-width*low-width*high))
    for i in xrange(num_e):
        aligned_data[i] = data[i, index_max[i] - center + width*low :
                               index_max[i] - center + num_vpe - width*high]

    return (aligned_data, center-width*low)

def clean(data, center):
    """
    remove outliers, i.e. events that have not been realigned,
    which means their maximum is far off the general maximum
    """
    index_max = data.argmax(1)
    return (data[index_max == center], (index_max != center))

def downsample(data, old_center, skip, new_center=19, num_points=64):
    """
    downsample data
    standard scheme:
    there are 64 points,
    maximum has index 19 (starting from 0)
    """
#    index = (arange(num_points) - new_center) * skip + old_center
    index = arange(num_points) * skip
    return data[:,index], num_points
