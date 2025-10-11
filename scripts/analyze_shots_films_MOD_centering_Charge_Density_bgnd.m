close all force;
clear all;
clear graphics;

set(0, 'defaultfigurevisible', 'off');

warning('off', 'Octave:shadowed-function');
warning('off', 'Octave:gnuplot-could-not-set-font');

% Global variables
global fname nshots Dose_center_all chargeRall nTest nCharge FileNames ChargeNames
global sig_x_all sig_y_all name_output calibration charge_calibration name_screen
global roi_shape roi_size bgnd_choice bgnd_file roi_image_path selected_masks

% Calibration constants
calibration = 1;
charge_calibration = 1.;
global T_calibration
T_calibration = calibration/charge_calibration;

% Image cropping parameters
dy = -35; % beam position adjustment: positive shifts beam up
dx = 0;   % beam position adjustment: positive shifts beam right
dxx = -30; % window reduction in all directions

DownCut = 116 + dy + dxx;
UpCut = 56 - dy + dxx;
LeftCut = 56 + dx + dxx;
RightCut = 56 - dx + dxx;

BGND_Type = 5; % default background type: edge-based
pixsizeX = 25.4/300; % pixel size in mm
pixsizeY = pixsizeX;

% Add functions directory to path
script_dir = fileparts(mfilename('fullpath'));
addpath(fullfile(script_dir, 'functions'));

npix = 10; % pixels for cross-section analysis

% Initialize GUI mode support
gui_mode = getenv('OCTAVE_GUI_MODE');
if strcmp(gui_mode, '1')
    script_dir = fileparts(mfilename('fullpath'));
    temp_results_file = fullfile(script_dir, 'temp_analysis_results.txt');

    fid = fopen(temp_results_file, 'w');
    fprintf(fid, 'Index\tFilename\tCharge_nC\tDose_with_BG_Gy\tDose_with_BG_std\tDose_CD\tDose_CD_std\tx0_mm\ty0_mm\txstd_mm\tystd_mm\n');
    fclose(fid);
endif

% Get user inputs
[roi_shape, roi_size, directory_films, ndata, datasets, ...
 roi_image_path, roi_mat_path, selected_masks, ...
 bgnd_choice, bgnd_file, bg_nums, main_nums, include_calib_plot, film_notes] = get_user_inputs();

tic;

n_main = length(main_nums);

% Pre-allocate result arrays
rmaxAll = zeros(1, n_main);
rmeanAll = zeros(1, n_main);
Dose_CD_all = zeros(1, n_main);
Dose_Gy_all = zeros(1, n_main);
Dose_with_BGND_Gy_all = zeros(1, n_main);
x0_Gy_all = zeros(1, n_main);
x0_with_BGND_Gy_all = zeros(1, n_main);
y0_Gy_all = zeros(1, n_main);
y0_with_BGND_Gy_all = zeros(1, n_main);
xstd_Gy_all = zeros(1, n_main);
xstd_with_BGND_Gy_all = zeros(1, n_main);
ystd_Gy_all = zeros(1, n_main);
ystd_with_BGND_Gy_all = zeros(1, n_main);
chargeAll = zeros(1, n_main);
film_name_all = cell(1, n_main);
Dose_CD_std_all = zeros(1, n_main);
Dose_Gy_std_all = zeros(1, n_main);
Dose_with_BGND_Gy_std_all = zeros(1, n_main);
Dose_ROI_mask_all = zeros(1, n_main);
Dose_ROI_mask_std_all = zeros(1, n_main);

% Process background
[use_existing_bgnd, compute_new_bgnd, image_bgnd, chargeAll_bgnd, BGND_Type, bgnd_file] = ...
    process_background(bgnd_choice, bgnd_file, bg_nums, directory_films, datasets);

% Set background for processing
if use_existing_bgnd || BGND_Type == 0
    current_bgnd = image_bgnd;
else
    current_bgnd = [];
endif

% Process main images
printf("Processing main image set...\n");
for i = 1:n_main
    file_idx = main_nums(i);
    if file_idx > ndata
        error(sprintf("Invalid file number: %d. Only %d files available.", file_idx, ndata));
    endif

    nTest = strcat(directory_films, datasets(file_idx).name);
    film_name = datasets(file_idx).name(1:length(datasets(file_idx).name)-4);
    film_name_all{i} = datasets(file_idx).name;
    data1 = load(nTest);
    imageF = double(data1.image_film_Gy);

    sizeall = size(imageF);
    charge = double(data1.charge);
    chargeAll(i) = charge;

    % Perform image analysis
    [Dose_Film, Dose_Film_nobgnd, Dose_Gauss, Dose_Exp_EBT3, Dose_Exp_XDWrong, nxF, nyF, nx, ny] = ...
        image_analysis_function(imageF, charge, current_bgnd, BGND_Type, DownCut, UpCut, LeftCut, RightCut, pixsizeX, pixsizeY);

    % Process dose with background
    name_output = strcat('Dose_Film_with-BGND_', film_name, '_Gy');
    [Dose_center_Film_with_BGND_Gy, xstd_BGND_Gy, ystd_BGND_Gy, x0_BGND_Gy, y0_BGND_Gy, bgnd_Dose_x, bgnd_Dose_y, Dose_center_Film_with_BGND_Gy_std] = ...
        plot_dose_function(Dose_Film, name_output, pixsizeX, pixsizeY, roi_size, npix, 1, roi_shape);

    % Process dose without background
    name_output = strcat('Dose_Film_', film_name, '_Gy');
    [Dose_center_Film_Gy, xstd_Gy, ystd_Gy, x0_Gy, y0_Gy, bgnd_Dose_x, bgnd_Dose_y, Dose_center_Film_Gy_std] = ...
        plot_dose_function(Dose_Film_nobgnd, name_output, pixsizeX, pixsizeY, roi_size, npix, 1, roi_shape);

    % Process dose in CD units
    name_output = strcat('Dose_Film_', film_name, '_CD');
    [Dose_center_Film_CD, xstd_CD, ystd_CD, x0_CD, y0_CD, bgnd_Dose_x, bgnd_Dose_y, Dose_center_Film_CD_std] = ...
        plot_dose_function(Dose_Gauss, name_output, pixsizeX, pixsizeY, roi_size, npix, T_calibration, roi_shape);

    % Process ROI mask if available
    if ~isempty(roi_mat_path) && ~isempty(selected_masks)
        [Dose_center_ROI_mask, Dose_center_ROI_mask_std] = calculate_roi_mask_dose(Dose_Film, roi_mat_path, selected_masks, DownCut, UpCut, LeftCut, RightCut);
        Dose_ROI_mask_all(i) = Dose_center_ROI_mask;
        Dose_ROI_mask_std_all(i) = Dose_center_ROI_mask_std;
    else
        Dose_ROI_mask_all(i) = 0;
        Dose_ROI_mask_std_all(i) = 0;
    endif

    % Store results
    Dose_CD_all(i) = Dose_center_Film_CD;
    Dose_Gy_all(i) = Dose_center_Film_Gy;
    Dose_with_BGND_Gy_all(i) = Dose_center_Film_with_BGND_Gy;
    x0_Gy_all(i) = x0_Gy;
    y0_Gy_all(i) = y0_Gy;
    x0_with_BGND_Gy_all(i) = x0_BGND_Gy;
    y0_with_BGND_Gy_all(i) = y0_BGND_Gy;
    xstd_Gy_all(i) = xstd_Gy;
    ystd_Gy_all(i) = ystd_Gy;
    xstd_with_BGND_Gy_all(i) = xstd_BGND_Gy;
    ystd_with_BGND_Gy_all(i) = ystd_BGND_Gy;
    Dose_CD_std_all(i) = Dose_center_Film_CD_std;
    Dose_Gy_std_all(i) = Dose_center_Film_Gy_std;
    Dose_with_BGND_Gy_std_all(i) = Dose_center_Film_with_BGND_Gy_std;

    % Update GUI temp file if in GUI mode
    if strcmp(gui_mode, '1')
        fid = fopen(temp_results_file, 'a');
        fprintf(fid, '%d\t%s\t%.2f\t%.2f\t%.2f\t%.2f\t%.2f\t%.2f\t%.2f\t%.2f\t%.2f\n', ...
                i, film_name, chargeAll(i), ...
                Dose_center_Film_with_BGND_Gy, Dose_center_Film_with_BGND_Gy_std, ...
                Dose_center_Film_CD, Dose_center_Film_CD_std, ...
                x0_Gy, y0_Gy, xstd_Gy, ystd_Gy);
        fclose(fid);
    endif

    % Handle zero charge case
    if charge == 0
        warning = 1;
        Dose_Gauss = zeros(size(Dose_Film_nobgnd)); % Create zero dose array with correct size
        Dose_Film = imageF(DownCut:nyF-UpCut, LeftCut:nxF-RightCut); % Extract film region
    endif

    % Calculate ratios
    rmax = max(Dose_Film_nobgnd(:)) / max(Dose_Gauss(:));
    rmean = mean(Dose_Film_nobgnd(:)) / mean(Dose_Gauss(:));

    rmaxAll(i) = rmax;
    rmeanAll(i) = rmean;

    printf("Processed main image %d of %d\n", i, n_main);
endfor

% Generate analysis report
generate_analysis_report(film_name_all, Dose_CD_all, Dose_with_BGND_Gy_all, ...
    Dose_Gy_all, Dose_ROI_mask_all, Dose_ROI_mask_std_all, ...
    x0_with_BGND_Gy_all, y0_with_BGND_Gy_all, ...
    xstd_with_BGND_Gy_all, ystd_with_BGND_Gy_all, ...
    Dose_CD_std_all, Dose_with_BGND_Gy_std_all, Dose_Gy_std_all, ...
    chargeAll, roi_shape, roi_size, bgnd_choice, bgnd_file, ...
    roi_image_path, selected_masks, include_calib_plot, film_notes);

% Clean up decompressed files
delete(strcat(directory_films, "*.dat"));

disp(['Analysis complete! Total time: ', num2str(toc), ' seconds']);
