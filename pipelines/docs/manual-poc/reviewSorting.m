% Here's an example script that loads and plots data from Kilosort's "rez"
% struct and Phy's various Numpy and other files.
%
% Setup:
%
% This requires "npy-matlab" to read Numpy data from Phy.
%
% - Clone The npy-matlab repo: https://github.com/kwikteam/npy-matlab
% - Add the repo to your Matlab path, for example:
%    addpath(genpath('/path/to/my/stuff/npy-matlab'))
%
% Inputs:
%
% This script reads data from a few sources -- files produced by running
% our plexon-kilosort-phy-fira pipeline.  The file paths and names are all
% specified near the top of this script and you can edit them for your
% local machine.
%
% - A file of results produced by Kilosort, "rez.mat".
% - A folder of results produced by Kilosort and Phy tool, containing
%    "params.py".
% - A file of results converted to the Gold Lab's FIRA format, like
%   "MM_2022_11_28C_V-ProRec-kilosort.mat".
%
% Outputs:
%
% This will read all of the above inputs into memory:
% - The "rez.mat" will end up in a "rez" variable.
% - Data from various Phy files including "params.py" will end up in a
% "phy" variable.
%
% - The Gold Lab FIRA data will be loaded into the global "FIRA" variable.
%
% This script will also plot several figures and save them as images into a
% "Review" folder in the same parent folder as "rez.mat".
%

clear;
clear global;
clc;
close all;

% Edit me.
monkeyDir = '/home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/';
resultsDir = fullfile(monkeyDir, 'Kilosort', 'MM_2022_11_28C_V-ProRec-results');
convertedFile = fullfile(monkeyDir, 'Converted', 'Sorted', 'MM_2022_11_28C_V-ProRec-kilosort.mat');

% Inputs.
rezFile = fullfile(resultsDir, 'rez.mat');
phyFile = fullfile(resultsDir, 'phy', 'params.py');
phyDir = fileparts(phyFile);

% Outputs.
figureDir = fullfile(resultsDir, 'Review');
if ~isfolder(figureDir)
    mkdir(figureDir);
end


%% Load Kilosort's "rez" output.

% Don't mind these: "Warning: Unable to load gpuArray data onto a GPU..."
rezRez = load(rezFile);
rez = rezRez.rez;


% Here's where each template is located along the probe -- I think.
% I copied this out of the Kilosort code here:
% https://github.com/MouseLand/Kilosort/blob/main/clustering/final_clustering.m#L28
uweigh = abs(rez.U(:,:,1));
uweigh = uweigh ./ sum(uweigh,1);
ycup = sum(uweigh .* rez.yc, 1);
xcup = sum(uweigh .* rez.xc, 1);


%% Plot spikes over space and time, for each cluster in the "rez".

% Use cluster depth for color-coding.
clusterDepths = sort(ycup);
colors = cool(numel(clusterDepths));

for cc = 1:numel(clusterDepths)
    % rez.st3 contains spike times plus some metadata for each spike.
    % The docs on this are not good.  As far as I can tell:
    %  - st(:,1) -- spike time, in sample numbers, not seconds.
    %  - st(:,2) -- spike cluster id
    %  - st(:,3) -- spike amplitude (what units?)
    %  - st(:,4) -- ??? mystery for the ages ???
    %  - st(:,5) -- processing "batch" number

    % rez.xy contains estimated probe position of each spike.
    % I didn't find docs on this, but it's in the kilosort code starting here:
    % https://github.com/MouseLand/Kilosort/blob/main/clustering/final_clustering.m#L65

    % rez.ops contains all the options we passed to Kilosort to begin with.
    % This includes sample frequency so we can get spike times in seconds.

    % Extract spike times and depths for each cluster.
    templateSelector = rez.st3(:, 2) == cc;
    spikeTimes = rez.st3(templateSelector, 1) / rez.ops.fs;
    spikePositions = rez.xy(templateSelector, 1);
    templatePositions = ycup(rez.st3(templateSelector, 2));

    % Put it all in a figure, color-coded based on the spike depth.
    figure()
    colorIndex = find(ycup(cc) == clusterDepths);
    color = colors(colorIndex, :);
    fadedColor = (color + [1 1 1]) / 2;
    hold on
    scatter(spikeTimes, spikePositions, '.', 'MarkerEdgeColor', fadedColor, 'DisplayName', 'dubious spike position');
    scatter(spikeTimes, templatePositions, '*', 'MarkerEdgeColor', color, 'DisplayName', 'template centroid');
    hold off
    xlabel('spike time (s)')
    yticks(sort(rez.yc));
    ylim([0, max(rez.yc)]);
    ylabel('probe location (um) (ticks at contacts)')
    grid('on');
    if rez.good(cc)
        goodOrNot = '"good"';
    else
        goodOrNot = 'not "good"';
    end
    clusterId = cc - 1;
    firingRate = numel(spikeTimes) / (rez.ops.sampsToRead / rez.ops.fs);
    title(sprintf('template %d (%s) (%d Hz)', clusterId, goodOrNot, round(firingRate)))
    legend();

    % Save an image of the figure for later and/or sharing.
    figureFile = fullfile(figureDir, sprintf('template-%d.png', clusterId));
    saveas(gcf, figureFile)
end


%% Load Phy's output from various files.

npyFiles = dir(fullfile(phyDir, '*.npy'));
for ii = 1:numel(npyFiles)
    npyFile = npyFiles(ii);
    data = readNPY(fullfile(npyFile.folder, npyFile.name));
    [~, fieldName] = fileparts(npyFile.name);
    phy.(genvarname(fieldName)) = data;
end

tsvFiles = dir(fullfile(phyDir, '*.tsv'));
for ii = 1:numel(tsvFiles)
    tsvFile = tsvFiles(ii);
    data = readtable(fullfile(tsvFile.folder, tsvFile.name), 'FileType', 'delimitedtext');
    [~, fieldName] = fileparts(tsvFile.name);
    phy.(genvarname(fieldName)) = data;
end

phy.params = struct();
lines = readlines(phyFile, 'EmptyLineRule', 'skip');
for ii = 1:numel(lines)
    line = lines{ii};
    rawSplits = split(line, '=');
    key = genvarname(strip(rawSplits{1}));
    value = strip(rawSplits{2});
    switch value
        case 'True'
            phy.params.(key) = true;
        case 'False'
            phy.params.(key) = false;
        otherwise
            phy.params.(key) = eval(rawSplits{2});
    end
end


%% Pick out clusters that Kilosort thougt were "good".

% This is also available in rez.good, but maybe we won't always use rez.

phyIds = phy.cluster_KSLabel.cluster_id;
phyIsGood = strcmp(phy.cluster_KSLabel.KSLabel, 'good');
champions = phyIds(phyIsGood);


%% Load Gold Lab FIRA data.

converted = load(convertedFile);
global FIRA
FIRA = converted.data;


%% Plot spikes from FIRA -- aligned to each trial start.

figure();
binWidth = 20;
binEdges = -100:binWidth:5000;
for cc = 1:numel(FIRA.spikes.id)
    spikeId = FIRA.spikes.id(cc);
    colorIndex = find(ycup(cc) == clusterDepths);
    color = colors(colorIndex, :);
    fadedColor = (color + [1 1 1]) / 2;

    spikeTimes = cat(1, FIRA.spikes.data{:, cc});
    spikeCounts = histcounts(spikeTimes, binEdges);
    spikesPerTrial = spikeCounts ./ FIRA.header.numTrials;
    firingRates = spikesPerTrial / binWidth * 1000;
    if any(spikeId == champions)
        lineWidth = 5;
        plot(binEdges(1:end-1), firingRates, '-', ...
            'LineWidth', lineWidth, ...
            'Color', color, ...
            'DisplayName', num2str(spikeId));
    else
        lineWidth = 0.5;
        p = plot(binEdges(1:end-1), firingRates, '-', ...
            'LineWidth', lineWidth, ...
            'Color', fadedColor);
        legendInfo = get(get(p, 'Annotation'), 'LegendInformation');
        set(legendInfo, 'IconDisplayStyle','off');
    end
    hold on
end

[~, baseName] = fileparts(convertedFile);
title(sprintf('%s -- Kilosort cluster timestamps, combined across trials, aligned to trial start.', baseName), 'Interpreter', 'none')
xlim([binEdges(1), binEdges(end)])
xlabel('trial time (s)')
ylabel('firing rate (Hz)')
legend()

% Save an image of the figure for later and/or sharing.
figureName = sprintf('%s_kilosort-cluster-timestamps.png', baseName);
saveas(gcf(), fullfile(figureDir, figureName));
