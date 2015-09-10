# JN 2015-01-11
# refactoring

from __future__ import division, print_function, absolute_import
import numpy as np
import scipy.stats as stats
from .. import options

def select_features(features):
    """
    select the features that go into sorting
    """
    factor = options['feature_factor']
    num_features_out = options['nFeatures']

    num_features = features.shape[1]

    feat_std = factor * features.std(0)
    feat_mean = features.mean(0)
    feat_up = feat_mean + feat_std
    feat_down = feat_mean - feat_std

    scores = np.zeros(num_features)

    for i in range(num_features):
        idx = (features[:, i] > feat_down[i]) & (features[:, i] < feat_up[i])
        if idx.any():
            good_features = features[idx, i]
            good_features = good_features - good_features.mean()
            good_features /= good_features.std()
            scores[i] = stats.kstest(good_features, 'norm')[1]

    sorted_scores = np.sort(scores)
    border = sorted_scores[num_features_out]
    ret = (scores <= border).nonzero()[0]
    ret = ret[:num_features_out]
    return ret


# test it
if __name__ == "__main__":
    data = np.random.normal(size=(1000, 64))
    data[:, [2, 4, 6]] = 1 # induce non-normality
    features = select_features(data)
    for i in [2, 4, 6]:
        assert i in features

    print('OK, features: ', features)
