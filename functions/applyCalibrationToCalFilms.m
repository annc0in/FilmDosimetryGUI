function [Dose, Dose_std] = applyCalibrationToCalFilms(cal_dir, liste, nb_files, window_meas, ...
    coeff1, Dose_Name_Gy, create_plots, save_plots)

    % Define ROI and crop parameters
    roi_rows = window_meas(1,1):window_meas(1,2);
    roi_cols = window_meas(2,1):window_meas(2,2);
    film_edges = [10 460 10 400];

    % Initialize result arrays
    Dose = zeros(1, nb_files);
    Dose_std = zeros(1, nb_files);
    Dose_non_Gy = zeros(1, nb_files);
    Dose_non_Gy_std = zeros(1, nb_files);

    % Create figure if needed
    if create_plots
        hfig = figure('Position', [10 10 1832 1022], 'Visible', 'off');
    end

    % Initialize 3D array for calibrated images
    if nb_files > 0
        temp_img = imread([cal_dir, liste(1).name]);
        temp_img = temp_img(film_edges(1):film_edges(2), film_edges(3):film_edges(4), :);
        Image_Gy = zeros(size(temp_img, 1), size(temp_img, 2), nb_files);
    end

    % Process each calibration film
    for i = 1:nb_files
        fprintf('\rProcessing calibration film %d of %d', i, nb_files);

        % Read and crop image
        Image = imread([cal_dir, liste(i).name]);
        Image = Image(film_edges(1):film_edges(2), film_edges(3):film_edges(4), :);
        Image_green = double(Image(:, :, 2));

        % Apply calibration
        Image_Gy(:, :, i) = polyval(coeff1, Image_green);

        % Extract ROI and calculate statistics
        Image_green_cut = Image_green(roi_rows, roi_cols);
        Image_sample = Image_Gy(roi_rows, roi_cols, i);

        Dose(i) = mean(Image_sample(:));
        Dose_std(i) = std(Image_sample(:));
        Dose_non_Gy(i) = mean(Image_green_cut(:));
        Dose_non_Gy_std(i) = std(Image_green_cut(:));

        % Create subplot if needed
        if create_plots
            subplot(4, ceil(nb_files/4), i);
            imagesc(Image_Gy(:, :, i), [0 25]);
            axis off; axis equal; hold on;

            % Draw ROI rectangle
            plot([window_meas(2, 1), window_meas(2, 2), window_meas(2, 2), window_meas(2, 1), window_meas(2, 1)], ...
                 [window_meas(1, 1), window_meas(1, 1), window_meas(1, 2), window_meas(1, 2), window_meas(1, 1)], 'r-');

            xlabel({['Del.dose: ', num2str(Dose_Name_Gy(i), '%.3f'), 'Gy'], ...
                ['\Delta = ', num2str(abs(Dose(i) - Dose_Name_Gy(i)), '%.3f'), 'Gy']}, ...
                'FontSize', 10, 'FontWeight', 'bold');
        end
    end

    % Save plot if needed
    if create_plots && save_plots
        cal_name = cal_dir(1:end-1);
        if ~isempty(strfind(cal_name, '/'))
            cal_name = cal_name(find(cal_name == '/', 1, 'last')+1:end);
        end

        validation_filename = ['check_', cal_name, '.png'];
        fprintf('\nSaving results to: %s\n', validation_filename);
        print(hfig, '-dpng', '-r150', validation_filename);
        close(hfig);
    end
end
