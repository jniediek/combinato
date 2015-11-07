TYPE_ALL = -3
TYPE_NON_NOISE = -2
TYPE_ART = -1
TYPE_NO = 0
TYPE_MU = 1
TYPE_SU = 2
CLID_UNMATCHED = 0


TYPE_NAMES = {TYPE_ART: 'Artifact',
              TYPE_NO: 'Not assigned',
              TYPE_MU: 'Multi-Unit',
              TYPE_SU: 'Single-Unit',
              TYPE_ALL: 'All spikes',
              TYPE_NON_NOISE: 'Non-noise spikes'}

GROUP_ART = -1
GROUP_NOCLASS = 0

SPIKE_MATCHED = 1
SPIKE_CLUST = 0
SPIKE_MATCHED_2 = 2  # for overall matching

SIGNS = ('pos', 'neg')
