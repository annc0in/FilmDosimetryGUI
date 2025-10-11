function [roi_shape, roi_size, directory_films, ndata, datasets, ...
          roi_image_path, roi_mat_path, selected_masks, ...
          bgnd_choice, bgnd_file, bg_nums, main_nums, include_calib_plot, film_notes] = get_user_inputs()

    pkg load io;

    json_filename = 'get_user_inputs.json';

    % Load previous settings if available
    if exist(json_filename, 'file')
        fid = fopen(json_filename, 'r');
        json_str = fread(fid, inf, 'char=>char')';
        fclose(fid);

        user_data = jsondecode(json_str);

        % Extract loaded values
        roi_shape = user_data.roi_shape;
        roi_size = user_data.roi_size;
        directory_films = user_data.directory_films;
        roi_image_path = user_data.roi_image_path;
        roi_mat_path = user_data.roi_mat_path;
        selected_masks = user_data.selected_masks(:)';
        bgnd_choice = user_data.bgnd_choice;
        bgnd_file = user_data.bgnd_file;
        bg_nums = user_data.bg_nums(:)';
        main_nums = user_data.main_nums(:)';
        include_calib_plot = user_data.include_calib_plot;
        film_notes = user_data.film_notes;

        % Display loaded settings
        printf("Loaded settings:\n");
        printf("  ROI shape: %s\n", roi_shape);
        printf("  ROI size: %g mm\n", roi_size);
        printf("  Directory: %s\n", directory_films);
        printf("  Background choice: %s\n", bgnd_choice);
        if strcmp(bgnd_choice, 'existing')
            printf("  Background file: %s\n", bgnd_file);
        elseif strcmp(bgnd_choice, 'compute')
            printf("  Background images: [%s]\n", num2str(bg_nums));
        endif
        printf("  Main images: [%s]\n", num2str(main_nums));
        printf("  Image of the lead films: %s\n", roi_image_path);
        printf("  Selected masks: [%s]\n", num2str(selected_masks));
        printf("  Include calibration plot: %d\n", include_calib_plot);

        % Check directory and find datasets
        if ~exist(directory_films, 'dir')
            error("Directory %s not found.", directory_films);
        endif

        path = [strcat(directory_films, "*.dat")];
        datasets = dir(path);
        ndata = length(datasets);
        printf("Found %d data files.\n", ndata);

        return;
    endif

    % No previous settings found - collect new inputs

    printf("Please select the shape of the central region for analysis:\n"); % Get ROI shape and size
    printf("1. Circle\n2. Square\n");
    shape_choice = input("Enter your choice (1 or 2): ");

    if shape_choice == 1
        roi_size = input("Enter the radius of the circle in mm: ");
        roi_shape = "circle";
    else
        roi_size = input("Enter the side length of the square in mm: ");
        roi_shape = "square";
    endif

    % Get directory name
    printf("Enter the directory name to use (e.g., 11_10_2024_prep_EBTXD_CALIBRATED): ");
    dir_name_input = input("", "s");
    directory_films = strcat('../', dir_name_input, '/');

    if ~exist(directory_films, 'dir')
        error("Directory %s not found.", directory_films);
    endif

    % Check for data files or extract archive
    path = [strcat(directory_films, "*.dat")];
    datasets = dir(path);
    ndata = length(datasets);

    if ndata == 0
        gzfile = glob(strcat(directory_films, "experimental_films_data.tar.gz"));
        if isempty(gzfile)
            error("No experimental_films_data.gz file found in the calibrated directory.");
        endif

        gz_filename = gzfile{1};
        untar(gz_filename, directory_films);

        datasets = dir(path);
        ndata = length(datasets);
    endif

    printf("Found %d data files.\n", ndata);

    % ROI Lead Mask Selection
    roi_image_path = '';
    roi_mat_path = '';
    selected_masks = [];

    % Find ROI images in parent directory
    roi_lead_dir = '../!ROIlead/';
    roi_png_pattern = strcat(roi_lead_dir, 'ROIlead_*.png');
    roi_png_files = glob(roi_png_pattern);

    if ~isempty(roi_png_files)
        available_pairs = {};
        pair_counter = 0;

        % Check for matching mat files
        for i = 1:length(roi_png_files)
            png_file = roi_png_files{i};
            [png_dir, png_name, ~] = fileparts(png_file);
            mat_file = strcat(png_dir, '/', png_name, '.mat');

            if exist(mat_file, 'file')
                pair_counter = pair_counter + 1;
                available_pairs{pair_counter} = struct('png', png_file, 'mat', mat_file, 'name', png_name);
            endif
        endfor

        if pair_counter > 0
            printf("Found %d ROI lead image pairs:\n", pair_counter);

            % Display available images
            figure_handles = [];
            for i = 1:pair_counter
                printf("%d. %s\n", i, available_pairs{i}.name);

                fig_handle = figure('visible', 'on', 'name', sprintf('ROI %d: %s', i, available_pairs{i}.name));
                figure_handles(end+1) = fig_handle;
                img = imread(available_pairs{i}.png);
                imshow(img);
                title(sprintf('ROI %d: %s', i, available_pairs{i}.name));
            endfor

            % Get user ROI selection
            roi_choice = input(sprintf("Select ROI image to use (1-%d): ", pair_counter));

            if roi_choice >= 1 && roi_choice <= pair_counter
                roi_image_path = available_pairs{roi_choice}.png;
                roi_mat_path = available_pairs{roi_choice}.mat;

                % Close non-selected images
                for i = 1:length(figure_handles)
                    if i ~= roi_choice
                        close(figure_handles(i));
                    endif
                endfor

                printf("Selected ROI: %s\n", available_pairs{roi_choice}.name);

                % Get mask numbers
                mask_input = input("Enter mask numbers to use (e.g., C018 - '18', C025-C027 - '25,26,27'): ", "s");
                selected_masks = str2num(strrep(mask_input, ",", " "));

                close(figure_handles(roi_choice));
            else
                % Close all figures if invalid selection
                for i = 1:length(figure_handles)
                    close(figure_handles(i));
                endfor
                printf("Invalid selection. Proceeding without ROI masks.\n");
            endif
        else
            printf("No matching ROI image-mat file pairs found.\n");
        endif
    else
        printf("No ROI lead images found in parent directory.\n");
    endif

    % Initialize empty ROI if no selection
    if isempty(roi_image_path)
        roi_image_path = '';
        selected_masks = [];
    endif

    % Background selection
    bgnd_files = glob('*bgnd*.mat');
    bgnd_choice = '';
    bgnd_file = '';
    bg_nums = [];

    % Display background options
    if ~isempty(bgnd_files)
        printf("Found existing background files:\n");
        for i = 1:length(bgnd_files)
            printf("%d. %s\n", i, bgnd_files{i});
        endfor
        printf("Options:\n");
        printf("- Enter file number (1-%d) to use existing background\n", length(bgnd_files));
        printf("- Enter 0 to compute new background\n- Press Enter to use edge-based background\n");
    else
        printf("No existing background files found.\n");
        printf("Options:\n");
        printf("- Enter 0 to compute averaged background\n- Press Enter to use edge-based background\n");
    endif

    user_choice = input("Your choice: ", "s");

    % Process background choice
    if isempty(user_choice)
        bgnd_choice = 'edge';
        printf("Using edge-based background detection.\n");
    elseif str2num(user_choice) == 0
        bgnd_choice = 'compute';
        printf("Will compute new background.\n");

        printf("Enter the file numbers for background images (e.g., 1-3 or 1,2,3): ");
        bg_nums_str = input("", "s");

        if ~isempty(strfind(bg_nums_str, "-"))
            parts = strsplit(bg_nums_str, "-");
            bg_start = str2num(parts{1});
            bg_end = str2num(parts{2});
            bg_nums = bg_start:bg_end;
        else
            bg_nums = str2num(strrep(bg_nums_str, ",", " "));
        endif
    else
        file_idx = str2num(user_choice);
        if file_idx >= 1 && file_idx <= length(bgnd_files)
            bgnd_choice = 'existing';
            bgnd_file = bgnd_files{file_idx};
            printf("Using background from: %s\n", bgnd_file);
        endif
    endif

    % Get main image numbers
    printf("Enter the file numbers for main image set (e.g., 4-6 or 4,5,6): ");
    main_nums_str = input("", "s");

    if ~isempty(strfind(main_nums_str, "-"))
        parts = strsplit(main_nums_str, "-");
        main_start = str2num(parts{1});
        main_end = str2num(parts{2});
        main_nums = main_start:main_end;
    else
        main_nums = str2num(strrep(main_nums_str, ",", " "));
    endif

    include_calib_plot = input("Include calibration plot in the pdf report? (1 - yes, 0 - no): ");

    % Get film notes
    n_main = length(main_nums);
    while true
        printf("Enter notes for each film (separated by commas, %d films total): ", n_main);
        notes_str = input("", "s");

        if isempty(notes_str)
            film_notes = cell(1, n_main);
            for i = 1:n_main
                film_notes{i} = '';
            endfor
            break;
        else
            notes_parts = strsplit(notes_str, ",");
            for i = 1:length(notes_parts)
                notes_parts{i} = strtrim(notes_parts{i});
            endfor

            if length(notes_parts) == n_main
                film_notes = notes_parts;
                break;
            else
                printf("Error: Number of notes (%d) doesn't match number of films (%d). Please try again.\n", ...
                       length(notes_parts), n_main);
            endif
        endif
    endwhile
endfunction
