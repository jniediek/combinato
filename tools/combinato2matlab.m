% JN 2022-04-26

% Convert sorted combinato output to Matlab files in Matlab.
% This is useful for working with Combinato outputs
% without using Python at all.

folder = '/home/johannes/Downloads/';
chan = 29;
label = 'joh';
sign = 'pos';


ffolder = fullfile(folder, sprintf('CSC%d', chan));
dfile = fullfile(ffolder, sprintf('data_CSC%d.h5', chan));
times = h5read(dfile, sprintf('/%s/times', sign));
waves = h5read(dfile, sprintf('/%s/spikes', sign));

full_label = sprintf('sort_%s_%s', sign, label);
sortfile = fullfile(ffolder, full_label, 'sort_cat.h5');

% the +1 is crucial because Python uses 0-based indexing, and Matlab
% 1-based indexing
idx = h5read(sortfile, '/index') + 1;

% reduce times/waves to those that were actually sorted (the rest are
% artifacts discarded before sorting)
times = times(idx);
waves = double(waves(:, idx));

% Combinato works with `groups` and `classes`. `groups` consist of several
% classes that are considered to belong to the same neuron.
groups = h5read(sortfile, '/groups');

unique_groups = unique(groups(2, :));
n_groups = length(unique_groups);

sp_times = cell(n_groups, 1);
sp_waveforms = cell(n_groups, 1);
sp_types = zeros(n_groups, 1);

classes = h5read(sortfile, '/classes');
classes = int16(classes);
types = h5read(sortfile, '/types');

for i = 1:n_groups
    gid = unique_groups(i);
    % find all classes that belong to the group gid
    cl_group = groups(1, groups(2, :) == gid);
    idx_cl = ismember(classes, cl_group);
    cl_times = times(idx_cl);
    sp_times{i} = cl_times;
    sp_waveforms{i} = waves(:, idx_cl);
    % save the type of group gid.
    % types are 0: artifact, 1: multi-unit 2: single unit
    sp_types(i) = types(2, types(1, :) == gid);
end

% save to file
outfname = sprintf('sorted_data_CSC%d_%s.mat', chan, sign);
save(outfname, 'sp_times', 'sp_waveforms', 'sp_types');