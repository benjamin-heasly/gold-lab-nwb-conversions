classdef Hdf5TrialFile

    properties (SetAccess = private)
        trialFile
        trialFields = { ...
            'start_time', ...
            'end_time', ...
            'wrt_time', ...
            'numeric_events', ...
            'signals', ...
            'enhancements', ...
            'enhancement_categories'}
    end

    methods

        function obj = Hdf5TrialFile(trialFile)
            arguments
                trialFile {mustBeFile}
            end
            obj.trialFile = trialFile;
        end

        function trials = readTrials(obj, indices)
            arguments
                obj Hdf5TrialFile
                indices {mustBeInteger} = []
            end

            % Load the trial file structure, but not data arrays.
            info = h5info(obj.trialFile);

            % Iterate the top-level HDF5 Groups -- ie trials.
            trialCell = {};
            index = 0;
            for trialGroup = info.Groups'
                % The first trial will get index 1, Matlab style.
                index = index + 1;

                % Only add trials at the requested indices.
                if ~isempty(indices) && ~any(index == indices)
                    continue
                end

                wildTrial = struct();

                % Get times and enhancements from HDF5 attributes.
                % Decode any trial enhancements from JSON.
                for attribute = trialGroup.Attributes'
                    switch attribute.Name
                        case 'enhancements'
                            wildTrial.enhancements = jsondecode(attribute.Value);
                        case 'enhancement_categories'
                            wildTrial.enhancement_categories = jsondecode(attribute.Value);
                        otherwise
                            wildTrial.(attribute.Name) = attribute.Value;
                    end
                end

                % Get data arrays from nested HDF5 groups.
                for dataGroup = trialGroup.Groups'
                    subgroupName = dataGroup.Name(numel(trialGroup.Name)+2:end);
                    switch subgroupName
                        case 'numeric_events'
                            for dataset = dataGroup.Datasets'
                                dataPath = [dataGroup.Name '/' dataset.Name];
                                data = h5read(obj.trialFile, dataPath);
                                if isempty(data)
                                    wildTrial.numeric_events.(dataset.Name) = [];
                                else
                                    wildTrial.numeric_events.(dataset.Name) = double(data');
                                end
                            end

                        case 'signals'
                            for dataset = dataGroup.Datasets'
                                dataPath = [dataGroup.Name '/' dataset.Name];
                                data = h5read(obj.trialFile, dataPath);
                                if isempty(data)
                                    wildTrial.signals.(dataset.Name).signal_data = [];
                                else
                                    wildTrial.signals.(dataset.Name).signal_data = double(data');
                                end

                                for attribute = dataset.Attributes'
                                    wildTrial.signals.(dataset.Name).(attribute.Name) = attribute.Value;
                                end
                            end
                    end
                end

                trial = obj.standardize(wildTrial);
                trialCell{end+1} = trial;
            end
            trials = [trialCell{:}];
        end

        function trial = standardize(obj, wildTrial)
            values = cell(size(obj.trialFields));
            for ii = 1:numel(obj.trialFields)
                name = obj.trialFields{ii};
                if isfield(wildTrial, name)
                    values{ii} = wildTrial.(name);
                end
            end
            trial = cell2struct(values, obj.trialFields, 2);
        end
    end
end
