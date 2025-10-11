function [use_existing_bgnd, compute_new_bgnd, image_bgnd, chargeAll_bgnd, BGND_Type, bgnd_file] = ...
    process_background(bgnd_choice, bgnd_file, bg_nums, directory_films, datasets)
% Process background images based on user selection

    use_existing_bgnd = false;
    compute_new_bgnd = false;
    image_bgnd = [];
    chargeAll_bgnd = [];
    BGND_Type = 5; % Default: edge-based background

    switch bgnd_choice
        case 'existing'
            load(bgnd_file);
            use_existing_bgnd = true;
            BGND_Type = 0;

        case 'compute'
            % Extract experiment ID from directory name
            [~, dir_name, ~] = fileparts(directory_films(1:end-1));
            calib_pos = strfind(dir_name, '_CALIBRATED');
            experiment_id = dir_name(1:calib_pos-1);

            n_bg = length(bg_nums);
            chargeAll_bgnd = zeros(1, n_bg);

            % Load first image to get dimensions
            nTest = strcat(directory_films, datasets(bg_nums(1)).name);
            data1 = load(nTest);
            bg_images = zeros([size(data1.image_film_Gy), n_bg]);

            % Load and average background images
            for i = 1:n_bg
                file_idx = bg_nums(i);
                nTest = strcat(directory_films, datasets(file_idx).name);
                data1 = load(nTest);
                bg_images(:,:,i) = double(data1.image_film_Gy);
                chargeAll_bgnd(i) = double(data1.charge);
            endfor

            image_bgnd = mean(bg_images, 3);
            bgnd_file = sprintf('bgnd_avg_%d-%d_from_%s.mat', min(bg_nums), max(bg_nums), experiment_id);
            save(bgnd_file, 'image_bgnd', 'chargeAll_bgnd', 'bg_nums');

            use_existing_bgnd = true;
            compute_new_bgnd = true;
            BGND_Type = 0;

        case 'edge'
            BGND_Type = 5; % Use edge-based background detection
    endswitch
end
