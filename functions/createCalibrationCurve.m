function [calibration_dir, coeff1, Dose_non_Gy, Dose_non_Gy_std, Dose_calAll, liste, nb_files] = ...
    createCalibrationCurve(window_meas, create_plots, save_plots, cal_dir, polynomial_degree)

    warning('off', 'Octave:shadowed-function');
    pkg load io;
    warning('on', 'Octave:shadowed-function');

    % Create output directory
    calibration_dir = '!CalibrationCurves/';
    if ~exist(calibration_dir, 'dir')
        mkdir(calibration_dir);
    end

    % Extract lot ID from directory name
    lot_pattern = 'Calibration_';
    if ~isempty(strfind(cal_dir, lot_pattern))
        lot_pos = strfind(cal_dir, lot_pattern);
        lot_id = cal_dir(lot_pos + length(lot_pattern):end-1);
    else
        lot_id = cal_dir(1:end-1);
    end

    % Define output filenames
    calibration_plot_file = [calibration_dir, 'polynomial_calibration_', lot_id, '.png'];
    calibration_data_file = [calibration_dir, 'data_polynomial_calibration_', lot_id, '.mat'];

    % Read dose values from Excel file
    excel_files = dir([cal_dir, '*.xlsx']);
    if isempty(excel_files)
        error('No Excel file found in calibration directory. Expected file with dose values.');
    end

    try
        [num_data] = xlsread([cal_dir, excel_files(1).name], '', 'F2:F100');
        Dose_cal = num_data(~isnan(num_data));

        if isempty(Dose_cal)
            error('No valid dose values found in Excel file (expected in column F).');
        end
    catch err
        error(['Failed to read dose values from Excel file: ', err.message]);
    end

    disp('Processing calibration films and creating calibration curve...');

    % Get film list
    liste = dir([cal_dir, '*.tif']);
    nb_files = length(liste);

    % Create dose array with duplicates (2 films per dose level)
    Dose_calAll = zeros(1, nb_files);
    for i=1:length(Dose_cal)
        idx1 = 2*i-1;
        idx2 = 2*i;
        if idx1 <= nb_files, Dose_calAll(idx1) = Dose_cal(i); end
        if idx2 <= nb_files, Dose_calAll(idx2) = Dose_cal(i); end
    end
    Dose_Name_Gy = Dose_calAll;

    % Initialize measurement arrays
    Dose_non_Gy = zeros(1, nb_files);
    Dose_non_Gy_std = zeros(1, nb_files);

    % Define ROI and crop parameters
    roi_rows = window_meas(1,1):window_meas(1,2);
    roi_cols = window_meas(2,1):window_meas(2,2);
    film_edges = [10 460 10 400];

    % Process each calibration film
    for i = 1:nb_files
        % Read and process image
        Image = imread([cal_dir, liste(i).name]);
        Image_green = double(Image(film_edges(1):film_edges(2), film_edges(3):film_edges(4), 2));

        % Calculate ROI statistics
        roi_vec = Image_green(roi_rows, roi_cols)(:);
        Dose_non_Gy(i) = mean(roi_vec);
        Dose_non_Gy_std(i) = std(roi_vec);
    end

    % Create polynomial calibration curve
    warning('off', 'Octave:singular-matrix');
    warning('off', 'Octave:nearly-singular-matrix');
    coeff1 = polyfit(Dose_non_Gy, Dose_Name_Gy, polynomial_degree);
    warning('on', 'Octave:singular-matrix');
    warning('on', 'Octave:nearly-singular-matrix');

    % Save calibration data
    if save_plots
        save(calibration_data_file, 'coeff1', 'Dose_non_Gy', 'Dose_non_Gy_std', 'Dose_calAll', '-v7');
    end

    % Generate calibration plot
    if create_plots
        hfig = figure('Position', [100 100 900 700]);

        % Create smooth curve
        xx = linspace(min(Dose_non_Gy)/1.1, max(Dose_non_Gy)*1.02, 1000);
        predicted = polyval(coeff1, xx);

        % Plot data and fit
        plot(Dose_non_Gy, Dose_Name_Gy, 'bo', 'MarkerSize', 6, 'MarkerFaceColor', [0.6 0.6 1], 'LineWidth', 0.5);
        hold on;
        plot(xx, predicted, 'r-', 'LineWidth', 1);

        % Format plot
        xlabel('Pixel Intensity (Green Channel)', 'FontSize', 12);
        ylabel('Dose (Gy)', 'FontSize', 12);
        title(['Calibration Curve'], 'FontSize', 14, 'FontWeight', 'bold');
        grid on;
        xlim([min(xx) max(xx)]);
        ylim([min(Dose_Name_Gy)*0.9 max(Dose_Name_Gy)*1.1]);

        legend_text = sprintf('%d%s Degree Polynomial Fit', polynomial_degree, getOrdinalSuffix(polynomial_degree));
        legend({'Measured Data', legend_text}, 'Location', 'northeast');

        set(gca, 'FontSize', 10, 'Box', 'on');
        drawnow;

        % Save plot
        if save_plots
            print(hfig, '-dpng', '-r300', calibration_plot_file);
            fprintf('Calibration curve is saved to %s\n', calibration_plot_file);
        end
    end
end

function suffix = getOrdinalSuffix(n)
    % Get ordinal suffix for numbers
    if n >= 11 && n <= 13
        suffix = 'th';
    else
        switch mod(n, 10)
            case 1
                suffix = 'st';
            case 2
                suffix = 'nd';
            case 3
                suffix = 'rd';
            otherwise
                suffix = 'th';
        end
    end
end
