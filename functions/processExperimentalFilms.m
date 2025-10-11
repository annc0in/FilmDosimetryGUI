function varargout = processExperimentalFilms(exp_dir, window_meas, varargin)

    gui_mode = ~isempty(getenv('OCTAVE_GUI_MODE'));
    gui_fid = -1;

    if nargin == 7
        % Using existing calibration
        chargeAll = varargin{1};
        create_plots = varargin{2};
        save_plots = varargin{3};
        selected_cal = varargin{4};
        selected_mat = varargin{5};

        calibration_dir = '!CalibrationCurves/';

        % Load calibration data
        loaded_data = load([calibration_dir, selected_mat]);
        coeff1 = loaded_data.coeff1;
        Dose_non_Gy = loaded_data.Dose_non_Gy;
        Dose_non_Gy_std = loaded_data.Dose_non_Gy_std;
        Dose_calAll = loaded_data.Dose_calAll;

        % Show calibration curve
        if create_plots
            figure('Position', [100 100 900 700]);
            imshow([calibration_dir, selected_cal]);
            drawnow;
        end

        % Return calibration data
        varargout{1} = coeff1;
        varargout{2} = Dose_non_Gy;
        varargout{3} = Dose_non_Gy_std;
        varargout{4} = Dose_calAll;

    elseif nargin == 6
        % Using new calibration
        coeff1 = varargin{1};
        chargeAll = varargin{2};
        create_plots = varargin{3};
        save_plots = varargin{4};
    else
        error('Invalid number of input arguments');
    end

    % Setup GUI mode file if needed
    if gui_mode
        tmp_file = 'octave_gui_data.txt';
        gui_fid = fopen(tmp_file, 'w');
        if gui_fid == -1
            warning('Could not create GUI data file');
            gui_mode = false;
        end
    end

    % Create output directory
    output_dir = [exp_dir(1:end-1), '_CALIBRATED/'];
    if ~exist(output_dir, 'dir')
        mkdir(output_dir);
    end

    % Get experimental films list
    list_films = dir([exp_dir, '*.tif']);
    nb_films = length(list_films);

    % Initialize result arrays
    Dose = zeros(1, nb_films);
    Dose_std = zeros(1, nb_films);
    Dose_Name_Film = zeros(1, nb_films);
    Dose_non_Gy = zeros(1, nb_films);
    Dose_non_Gy_std = zeros(1, nb_films);
    dat_files = cell(nb_films, 1);

    % Initialize 3D array for calibrated images
    if nb_films > 0
        temp_img = imread([exp_dir, list_films(1).name]);
        Image_Gy = zeros(size(temp_img, 1), size(temp_img, 2), nb_films);
    end

    % Create figure if needed
    if create_plots
        hfig = figure(11, 'Position', [10 10 1832 1022], 'Visible', 'off');
    end

    % Process each experimental film
    for i = 1:nb_films
        fprintf('\rProcessing experimental film %d of %d', i, nb_films);

        file_name = list_films(i).name;
        charge = chargeAll(i);

        % Extract film number from filename
        Dose_Name_Film(i) = str2num(file_name(3:end-4));
        Dose_Name_This = file_name(1:end-4);

        % Read and crop image
        Image = imread([exp_dir, file_name]);
        Image_uncut = Image;
        film_edges = [10, size(Image_uncut, 1)-10, 10, size(Image_uncut, 2)-10];
        Image = Image(film_edges(1):film_edges(2), film_edges(3):film_edges(4), :);
        Image_green = double(Image(:, :, 2));

        % Calculate center and ROI
        image_height = size(Image, 1);
        image_width = size(Image, 2);
        center_y = round(image_height / 2);
        center_x = round(image_width / 2);

        % Define square ROI
        roi_size = round(min(60, min(image_height, image_width) / 6));
        roi_y_min = round(center_y - roi_size / 2);
        roi_y_max = round(center_y + roi_size / 2);
        roi_x_min = round(center_x - roi_size / 2);
        roi_x_max = round(center_x + roi_size / 2);

        film_window_meas = [roi_y_min roi_y_max; roi_x_min roi_x_max];
        roi_rows = film_window_meas(1,1):film_window_meas(1,2);
        roi_cols = film_window_meas(2,1):film_window_meas(2,2);

        % Apply calibration
        image_film_Gy = polyval(coeff1, Image_green);

        % Calculate statistics
        Image_green_cut = Image_green(roi_rows, roi_cols);
        Image_sample = image_film_Gy(roi_rows, roi_cols);

        Dose(i) = mean(Image_sample(:));
        Dose_std(i) = std(Image_sample(:));
        Dose_non_Gy(i) = mean(Image_green_cut(:));
        Dose_non_Gy_std(i) = std(Image_green_cut(:));

        % Write GUI data if needed
        if gui_mode && gui_fid ~= -1
            json_msg = sprintf('[FILM_DATA]{"num":"%s","name":"%s","dose":%.3f,"std":%.3f,"charge":%.2f}', ...
                file_name(1:end-4), file_name, Dose(i), Dose_std(i), chargeAll(i));
            fprintf(gui_fid, '%s\n', json_msg);
            fflush(gui_fid);
        end

        % Save calibrated data
        temp_file = [output_dir, Dose_Name_This, '.dat'];
        save('-text', temp_file, 'charge', 'image_film_Gy');
        dat_files{i} = temp_file;

        % Create subplot if needed
        if create_plots
            subplot(4, ceil(nb_films/4), i);
            imagesc(image_film_Gy, [0 25]);
            axis off; axis equal; hold on;

            % Draw ROI rectangle
            plot([film_window_meas(2, 1), film_window_meas(2, 2), film_window_meas(2, 2), film_window_meas(2, 1), film_window_meas(2, 1)], ...
                 [film_window_meas(1, 1), film_window_meas(1, 1), film_window_meas(1, 2), film_window_meas(1, 2), film_window_meas(1, 1)], 'r-');

            xlabel([list_films(i).name(1:end-4), ': ', num2str(Dose(i), '%.3f'), 'Gy'], ...
                'FontSize', 10, 'FontWeight', 'bold', 'Interpreter', 'none');
        end
    end

    if gui_mode && gui_fid ~= -1
        fclose(gui_fid);
    end

    % Save plot if needed
    if create_plots && save_plots
        processed_dir = '!Processed/';
        if ~exist(processed_dir, 'dir')
            mkdir(processed_dir);
        end

        exp_name = exp_dir(1:end-1);
        if ~isempty(strfind(exp_name, '/'))
            exp_name = exp_name(find(exp_name == '/', 1, 'last')+1:end);
        end

        experimental_filename = [processed_dir, 'polynomial_calibration_', exp_name, '.png'];
        fprintf('\nSaving results to: %s\n', experimental_filename);
        print(hfig, '-dpng', '-r250', experimental_filename);
        close(hfig);
    end

    % Create compressed archive
    disp('Creating compressed archive of .dat files...');
    if ~isempty(dat_files)
        current_dir = pwd;
        cd(output_dir);

        % Prepare filenames for archiving
        file_names = cell(nb_films, 1);
        for i = 1:nb_films
            [~, name, ext] = fileparts(dat_files{i});
            file_names{i} = [name, ext];
        end

        % Create archive
        if ispc
            system('"C:\Windows\System32\tar.exe" -czf experimental_films_data.tar.gz *.dat');
        else
            system('tar -czf experimental_films_data.tar.gz *.dat');
        end

        delete('*.dat');
        cd(current_dir);
    end
end
