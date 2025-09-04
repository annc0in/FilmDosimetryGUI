function analyzeLeadRegion(exp_dir, coeff1, lead_films, lead_mask_type, rect_height_mm)
    % Analyze lead region on specified films and apply mask to all .tif films
    printf("Analyzing lead region...\n");

    pkg load image

    % Get sorted list of all .tif files
    files = dir([exp_dir, '*.tif']);
    filenames = sort({files.name});
    n = numel(filenames);

    % Find indices of lead films
    lead_indices = [];
    lead_film_names = {};
    for i = 1:length(lead_films)
        film_pattern = sprintf('[A-Z]_?%03d(\\D|$)', lead_films(i));
        idx = find(~cellfun('isempty', regexp(filenames, film_pattern)), 1);
        if ~isempty(idx)
            lead_indices(end+1) = idx;
            lead_film_names{end+1} = filenames{idx};
        end
    end

    % Store lead masks and boundaries
    lead_masks = cell(length(lead_indices), 1);
    lead_boundaries = cell(length(lead_indices), 1);
    lead_roi_coords = cell(length(lead_indices), 1);

    % Process each lead film
    for i = 1:length(lead_indices)
        lead_idx = lead_indices(i);
        lead_name = filenames{lead_idx};

        % Load and crop image
        I_lead_full = imread([exp_dir, lead_name]);
        film_edges = [10, size(I_lead_full, 1)-10, 10, size(I_lead_full, 2)-10];
        I_lead = I_lead_full(film_edges(1):film_edges(2), film_edges(3):film_edges(4), :);

        Ig = double(I_lead(:, :, 2));
        [h, w] = size(Ig);
        cx = round(w / 2);
        cy = round(h / 2);

        % Extract central region for mask computation
        roi_size = round(min(500, min(h, w) / 5.1));
        y1 = cy - floor(roi_size / 2);
        y2 = cy + floor(roi_size / 2);
        x1 = cx - floor(roi_size / 2);
        x2 = cx + floor(roi_size / 2);
        sub = Ig(y1:y2, x1:x2);
        subn = (sub - min(sub(:))) / (max(sub(:)) - min(sub(:)));
        subn = imgaussfilt(subn, 1.2);
        thresh = graythresh(subn);
        mask = subn > thresh;
        mask = bwareaopen(mask, 40);
        mask = imfill(mask, 'holes');
        mask(round(end*0.65):end, :) = 0;

        % Extract largest object as lead region
        CC = bwconncomp(mask);
        areas = cellfun(@numel, CC.PixelIdxList);
        [~, iMax] = max(areas);
        mask_clean = false(size(mask));
        mask_clean(CC.PixelIdxList{iMax}) = true;

        if strcmp(lead_mask_type, 'rectangle')
            % Compute rectangle mask
            [yy, xx] = find(mask_clean);
            bottom_y = max(yy);

            % Convert height from mm to pixels
            dpi = 300;
            rect_height_px = round(rect_height_mm * dpi / 25.4);

            % Define rectangle boundaries
            top_y = max(bottom_y - rect_height_px + 1, 1);
            x_min = min(xx);
            x_max = max(xx);

            rect_mask = false(size(mask_clean));
            rect_mask(top_y:bottom_y, x_min:x_max) = true;
            mask_clean = rect_mask;
        end

        % Convert to full-size mask
        full_mask = false(h, w);
        full_mask(y1:y2, x1:x2) = mask_clean;

        % Store mask and boundary
        lead_masks{i} = full_mask;
        B = bwboundaries(mask_clean);
        lead_boundaries{i} = B{1};
        lead_roi_coords{i} = struct('y1', y1, 'y2', y2, 'x1', x1, 'x2', x2);
    end

    % Create filenames
    exp_name = exp_dir(1:end-1);
    if ~isempty(strfind(exp_name, '/'))
        exp_name = exp_name(find(exp_name == '/', 1, 'last')+1:end);
    end

    lead_str = '';
    for i = 1:length(lead_films)
        if i == 1
            lead_str = num2str(lead_films(i));
        else
            lead_str = [lead_str, '_', num2str(lead_films(i))];
        end
    end

    % Create output directory
    roilead_dir = '!ROIlead/';
    if ~exist(roilead_dir, 'dir')
        mkdir(roilead_dir);
    end

    % Save lead region data
    mat_filename = [roilead_dir, sprintf('ROIlead_%s_from_%s.mat', lead_str, exp_name)];
    lead_data = struct();
    for i = 1:length(lead_indices)
        film_num = lead_films(i);
        field_name = sprintf('film_%d', film_num);
        [mask_rows, mask_cols] = find(lead_masks{i});
        lead_data.(field_name) = struct(...
            'film_number', film_num, ...
            'mask_pixel_coords', [mask_rows, mask_cols], ...
            'full_mask', lead_masks{i}, ...
            'roi_coords', lead_roi_coords{i});
    end
    save('-v7', mat_filename, 'lead_data');
    printf("Lead region data saved to: %s\n", mat_filename);

    % Setup visualization parameters
    dpi = 300;
    r_mm = 2;
    r_px = round(r_mm * dpi / 25.4);
    p = linspace(0, 2*pi, 300);
    cross_len = round(0.8 * r_px);

    % Create figure
    hfig = figure(12, 'Position', [10 10 1832 1022], 'Visible', 'off');
    clim = [0 25];

    % Calculate grid layout
    n_lead = length(lead_indices);
    if n_lead <= 5
        ncols = ceil(n_lead); nrows = 1;
    else
        ncols = 5; nrows = ceil(n_lead / 5);
    end

    gap = [0.01 0.03];
    marg_h = [0.3 0.01];
    marg_w = [0.02 0.02];

    % Process lead films for display
    for i = 1:n_lead
        lead_idx = lead_indices(i);
        fname = filenames{lead_idx};

        % Read and crop image
        I_full = imread([exp_dir, fname]);
        film_edges = [10, size(I_full, 1)-10, 10, size(I_full, 2)-10];
        I = I_full(film_edges(1):film_edges(2), film_edges(3):film_edges(4), :);

        Ig = double(I(:, :, 2));
        Id = polyval(coeff1, Ig);
        [h, w] = size(Ig);
        cx = round(w / 2);
        cy = round(h / 2);

        % Create coordinate grid
        [X, Y] = meshgrid(1:w, 1:h);
        circle_mask = (X - cx).^2 + (Y - cy).^2 <= r_px^2;
        circ_x = cx + r_px * cos(p);
        circ_y = cy + r_px * sin(p);

        % Calculate dose statistics
        full_mask = lead_masks{i};
        d_roi = mean(Id(full_mask));
        s_roi = std(Id(full_mask));
        d_ctr = mean(Id(circle_mask));
        s_ctr = std(Id(circle_mask));

        % Calculate subplot position
        row = ceil(i / ncols);
        col = mod(i - 1, ncols) + 1;
        subplot_width = (1 - marg_w(1) - marg_w(2) - (ncols-1)*gap(2)) / ncols;
        subplot_height = (1 - marg_h(1) - marg_h(2) - (nrows-1)*gap(1)) / nrows;
        pos_x = marg_w(1) + (col-1) * (subplot_width + gap(2));
        pos_y = 1 - marg_h(2) - row * subplot_height - (row-1) * gap(1);

        % Create subplot
        ax = subplot('Position', [pos_x, pos_y, subplot_width, subplot_height]);
        imagesc(Id, [0 25]);
        axis off; axis equal; hold on;

        % Draw overlays
        b = lead_boundaries{i};
        roi_coords = lead_roi_coords{i};
        plot(b(:,2) + roi_coords.x1 - 1, b(:,1) + roi_coords.y1 - 1, 'r-', 'LineWidth', 1.2);
        plot(circ_x, circ_y, 'k--', 'LineWidth', 1);
        plot([cx - cross_len, cx + cross_len], [cy, cy], 'k-', 'LineWidth', 1);
        plot([cx, cx], [cy - cross_len, cy + cross_len], 'k-', 'LineWidth', 1);

        film_number = str2num(fname(3:end-4));
        film_title = fname(1:end-4);

        if n_lead <= 5
            font_size = 14;
        else
            font_size = 9;
        end
        xlabel({film_title, ...
                ['ROI: ', num2str(d_roi, '%.3f'), ' ± ', num2str(s_roi, '%.3f'), ' Gy'], ...
                ['Center: ', num2str(d_ctr, '%.3f'), ' ± ', num2str(s_ctr, '%.3f'), ' Gy']}, ...
                'FontSize', font_size, 'FontWeight', 'bold', 'Interpreter', 'none');
    end

    % Save visualization
    png_filename = [roilead_dir, sprintf('ROIlead_%s_from_%s.png', lead_str, exp_name)];
    print(hfig, '-dpng', '-r150', png_filename);
    close(hfig);
    printf("Lead region visualization saved to: %s\n", png_filename);
end
