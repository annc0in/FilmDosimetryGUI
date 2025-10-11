function [use_existing_calibration, selected_cal, selected_mat, cal_dir, exp_dir, chargeAll, lead_films, validate_calibration, polynomial_degree, lead_mask_type, rect_height_mm] = getUserInputs()

    pkg load io;

    json_filename = 'user_inputs.json';

    % Load previous inputs if available
    if exist(json_filename, 'file')
        fid = fopen(json_filename, 'r');
        json_str = fread(fid, inf, 'char=>char')';
        fclose(fid);

        user_data = jsondecode(json_str);

        % Extract values
        use_existing_calibration = user_data.use_existing_calibration;
        selected_cal = user_data.selected_cal;
        selected_mat = user_data.selected_mat;
        cal_dir = user_data.cal_dir;
        exp_dir = user_data.exp_dir;
        chargeAll = user_data.chargeAll(:)';
        lead_films = user_data.lead_films(:)';
        validate_calibration = user_data.validate_calibration;
        polynomial_degree = user_data.polynomial_degree;
        lead_mask_type = user_data.lead_mask_type;

        % Handle backward compatibility
        if isfield(user_data, 'rect_height_mm')
            rect_height_mm = user_data.rect_height_mm;
        else
            rect_height_mm = 0;
        end

        % Display loaded settings
        disp('Loaded settings:');
        if use_existing_calibration
            disp(['  Selected calibration: ', selected_cal]);
        else
            disp(['  Calibration directory: ', cal_dir]);
            disp(['  Validate calibration: ', num2str(validate_calibration)]);
            disp(['  Polynomial degree: ', num2str(polynomial_degree)]);
        end
        disp(['  Experimental directory: ', exp_dir]);
        disp(['  Charge values: [', num2str(chargeAll), ']']);
        disp(['  Lead films: [', num2str(lead_films), ']']);
        disp(['  Lead mask type: ', lead_mask_type]);
        if strcmp(lead_mask_type, 'rectangle')
            disp(['  Rectangle height: ', num2str(rect_height_mm), ' mm']);
        end

        return;
    end

    calibration_dir = '!CalibrationCurves/';

    % Find valid calibrations (PNG with matching MAT files)
    calibration_files = dir([calibration_dir, 'polynomial_calibration_*.png']);
    valid_calibrations = {};
    valid_indices = [];

    for i = 1:length(calibration_files)
        png_name = calibration_files(i).name;
        mat_name = ['data_', png_name(1:end-4), '.mat'];

        if exist([calibration_dir, mat_name], 'file')
            valid_calibrations{end+1} = png_name;
            valid_indices(end+1) = i;
        end
    end

    % Initialize defaults
    use_existing_calibration = false;
    selected_cal = '';
    selected_mat = '';
    validate_calibration = false;
    polynomial_degree = 8;

    % Prompt for calibration choice
    if ~isempty(valid_calibrations)
        disp('Available calibration curves:');
        for i = 1:length(valid_calibrations)
            disp([num2str(i), '. ', valid_calibrations{i}]);
        end

        choice = input('Enter calibration number to use (0 for new calibration): ');

        if choice > 0 && choice <= length(valid_calibrations)
            use_existing_calibration = true;
            selected_cal = valid_calibrations{choice};
            selected_mat = ['data_', selected_cal(1:end-4), '.mat'];
            cal_dir = '';
        end
    end

    % Get new calibration parameters if needed
    if ~use_existing_calibration
        cal_dir = input('Enter calibration films directory (e.g. LOT_02232301_19-05-23/): ', 's');
        if cal_dir(end) ~= '/', cal_dir = [cal_dir, '/']; end

        validate_calibration_input = lower(input('Validate calibration on reference films? (y/n): ', 's'));
        validate_calibration = (validate_calibration_input(1) == 'y');

        while true
            polynomial_degree = input('Enter polynomial degree for calibration curve (1-15, default 8): ');
            if isempty(polynomial_degree)
                polynomial_degree = 8;
                break;
            elseif polynomial_degree >= 1 && polynomial_degree <= 15
                break;
            else
                disp('Polynomial degree must be between 1 and 15. Please try again.');
            end
        end
    end

    % Get experimental directory
    exp_dir = input('Enter experimental films directory (e.g. 11_10_2024_prep_EBTXD/): ', 's');
    if exp_dir(end) ~= '/', exp_dir = [exp_dir, '/']; end

    % Get charge values
    list_films = dir([exp_dir, '*.tif']);
    while true
        charge_input = input(sprintf('Found %d films. Enter charges (comma-separated) or "0" for all zeros: ', length(list_films)), 's');

        if strcmp(strtrim(charge_input), '0')
            chargeAll = zeros(1, length(list_films));
            break;
        else
            chargeAll = str2num(['[' charge_input ']']);
            if numel(chargeAll) == length(list_films), break; end
            disp(sprintf('Expected %d values, got %d. Try again.', length(list_films), numel(chargeAll)));
        end
    end

    % Get lead films
    lead_input = input('Enter film numbers for lead region analysis (e.g. 25,28 or 25-28): ', 's');

    % Parse film numbers
    if ~isempty(strfind(lead_input, '-'))
        dash_pos = strfind(lead_input, '-');
        start_num = str2num(lead_input(1:dash_pos(1)-1));
        end_num = str2num(lead_input(dash_pos(1)+1:end));
        lead_films = start_num:end_num;
    else
        lead_films = str2num(['[' lead_input ']']);
    end

    % Get lead mask type
    lead_mask_type_input = lower(strtrim(input('Use full lead mask (default) or rectangle? (f/r): ', 's')));
    if lead_mask_type_input == 'r'
        lead_mask_type = 'rectangle';

        while true
            rect_height_mm = input('Enter rectangle mask height in mm (positive number): ');
            if isnumeric(rect_height_mm) && rect_height_mm > 0
                break;
            else
                disp('Invalid input. Enter a positive number.');
            end
        end
    else
        lead_mask_type = 'full';
        rect_height_mm = 0;
    end
end
