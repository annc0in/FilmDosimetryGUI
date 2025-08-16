function Check_calibration_XD_add_films()

    gui_mode = ~isempty(getenv('OCTAVE_GUI_MODE'));
    if gui_mode
        set(0, 'defaultfigurevisible', 'off');
    end

    close all;
    clear all;

    script_dir = fileparts(mfilename('fullpath'));
    addpath(fullfile(script_dir, 'functions'));

    % Configuration flags
    create_plots = true;
    save_plots = true;

    % Get user inputs
    [use_existing_calibration, selected_cal, selected_mat, cal_dir, exp_dir, chargeAll, lead_films, validate_calibration, polynomial_degree, lead_mask_type, rect_height_mm] = ...
        getUserInputs();

    % Define measurement window coordinates [y_range; x_range]
    window_meas = [200 300; 180 220];

    tic;

    if use_existing_calibration
        % Process with existing calibration
        [coeff1, Dose_non_Gy, Dose_non_Gy_std, Dose_calAll] = ...
            processExperimentalFilms(exp_dir, window_meas, chargeAll, create_plots, save_plots, ...
            selected_cal, selected_mat);
    else
        % Create new calibration curve
        [calibration_dir, coeff1, Dose_non_Gy, Dose_non_Gy_std, Dose_calAll, liste, nb_files] = ...
            createCalibrationCurve(window_meas, create_plots, save_plots, cal_dir, polynomial_degree);

        % Validate calibration if requested
        if validate_calibration
            Dose_Name_Gy = Dose_calAll;
            [Dose, Dose_std] = applyCalibrationToCalFilms(cal_dir, liste, nb_files, window_meas, ...
                coeff1, Dose_Name_Gy, create_plots, save_plots);
        end

        % Process experimental films
        processExperimentalFilms(exp_dir, window_meas, coeff1, chargeAll, create_plots, save_plots);
    end

    % Process lead region analysis
    analyzeLeadRegion(exp_dir, coeff1, lead_films, lead_mask_type, rect_height_mm);

    disp(['Processing complete! Total time: ', num2str(toc), ' seconds']);
end
