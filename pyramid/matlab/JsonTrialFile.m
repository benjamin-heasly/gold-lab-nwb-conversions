classdef JsonTrialFile

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

        function obj = JsonTrialFile(trialFile)
            arguments
                trialFile {mustBeFile}
            end
            obj.trialFile = trialFile;
        end

        function trials = readTrials(obj, indices)
            arguments
                obj JsonTrialFile
                indices {mustBeInteger} = []
            end

            % Open the trial file and auto-close it on exit.
            fid = fopen(obj.trialFile, 'r');
            cleanup = onCleanup(@()fclose(fid));

            % Iterate the lines of the file -- ie trials.
            trialCell = {};
            index = 0;
            while true
                % Check for end of file.
                trialJson = fgetl(fid);
                if ~ischar(trialJson) || isempty(trialJson)
                    break
                end

                % The first trial will get index 1, Matlab style.
                index = index + 1;

                % Only add trials at the requested indices.
                if ~isempty(indices) && ~any(index == indices)
                    continue
                end

                wildTrial = jsondecode(trialJson);
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
