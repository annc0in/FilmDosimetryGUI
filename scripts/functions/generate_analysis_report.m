function generate_analysis_report(film_names, Dose_CD_all, Dose_with_BGND_Gy_all, Dose_Gy_all, ...
                                Dose_ROI_mask_all, Dose_ROI_mask_std_all, ...
                                x0_all, y0_all, xstd_all, ystd_all, ...
                                Dose_CD_std_all, Dose_with_BGND_Gy_std_all, Dose_Gy_std_all, ...
                                chargeAll, roi_shape, roi_size, bgnd_choice, bgnd_file, ...
                                roi_image_path, selected_masks, include_calib_plot, film_notes)

    % Initialize PDF report
    printf("Generating PDF report...\n");
    warning('off', 'all');
    outfile = "analysis_report";
    current_toolkit = graphics_toolkit();
    graphics_toolkit("gnuplot");

    % Calculate calibration coefficients
    calibration_ratios1 = Dose_with_BGND_Gy_all ./ Dose_CD_all;
    calibration_ratios2 = Dose_Gy_all ./ Dose_CD_all;
    avg_calibration_coeff1 = mean(calibration_ratios1);
    avg_calibration_coeff2 = mean(calibration_ratios2);
    std_calibration_coeff1 = std(calibration_ratios1);
    std_calibration_coeff2 = std(calibration_ratios2);
    calibrated_dose_cd1 = Dose_CD_all * avg_calibration_coeff1;
    calibrated_dose_cd2 = Dose_CD_all * avg_calibration_coeff2;

    % --- PAGE 1: Analysis Results ---
    figure('visible', 'off', 'PaperUnits', 'centimeters', 'PaperSize', [21 29.7], 'PaperPosition', [0.5 0.5 20 28.7]);

    % 1. Doses Plot
    subplot('Position', [0.1 0.74 0.8 0.20]);
    hold on;
    n = length(Dose_CD_all);
    x_vals = 1:n;

    % Plot with proper Octave-compatible error bars
    h1 = errorbar(x_vals, Dose_with_BGND_Gy_all, Dose_with_BGND_Gy_std_all, '~');
    set(h1, 'linestyle', 'none', 'linewidth', 1.2, 'color', [0.2 0.4 0.8]);
    h1_plot = plot(x_vals, Dose_with_BGND_Gy_all, '-o', 'linewidth', 1.2, 'markerfacecolor', [0.2 0.4 0.8], 'color', [0.2 0.4 0.8], 'markersize', 4.5);

    h2 = errorbar(x_vals, Dose_Gy_all, Dose_Gy_std_all, '~');
    set(h2, 'linestyle', 'none', 'linewidth', 1.2, 'color', [0.2 0.8 0.2]);
    h2_plot = plot(x_vals, Dose_Gy_all, '-d', 'linewidth', 1.2, 'markerfacecolor', [0 0.6 0], 'color', [0 0.6 0], 'markersize', 4.5);

    h3 = errorbar(x_vals, Dose_CD_all, Dose_CD_std_all, '~');
    set(h3, 'linestyle', 'none', 'linewidth', 1, 'color', [0.8 0.2 0.2]);
    h3_plot = plot(x_vals, Dose_CD_all, '-s', 'linewidth', 1, 'markerfacecolor', [0.8 0.2 0.2], 'color', [0.8 0.2 0.2], 'markersize', 3.5);

    if any(Dose_ROI_mask_all > 0)
        h4 = errorbar(x_vals, Dose_ROI_mask_all, Dose_ROI_mask_std_all, '~');
        set(h4, 'linestyle', 'none', 'linewidth', 1.2, 'color', [0.9 0.8 0]);
        h4_plot = plot(x_vals, Dose_ROI_mask_all, '-^', 'linewidth', 1.2, 'markerfacecolor', [0.9 0.8 0], 'color', [0.9 0.8 0], 'markersize', 4.5);
    else
        h4_plot = [];
    endif

    h5_plot = plot(x_vals, calibrated_dose_cd1, '-x', 'linewidth', 1.3, 'color', [0.5 0 0.8], 'markersize', 3, 'markeredgecolor', [0.5 0 0.8]);

    h6_plot = plot(x_vals, calibrated_dose_cd2, '-x', 'linewidth', 1.3, 'color', [1 0.6 0.8], 'markersize', 3, 'markeredgecolor', [1 0.6 0.8]);

    % Format plot to match original
    xlim([0.5, n + 0.5]);
    xticks(x_vals);
    xlabel('Film #', 'FontSize', 9);
    ylabel('Dose center [Gy]', 'FontSize', 9);
    title('Measured Doses', 'FontSize', 10);
    grid on;
    set(gca, 'FontSize', 8);

    % Add complete grid borders
    ax = gca;
    set(ax, 'Layer', 'bottom');
    y_lims = ylim;
    x_lims = xlim;
    line([x_lims(1) x_lims(2)], [y_lims(2) y_lims(2)], 'Color', [0.15 0.15 0.15], 'LineWidth', 0.5);
    line([x_lims(2) x_lims(2)], [y_lims(1) y_lims(2)], 'Color', [0.15 0.15 0.15], 'LineWidth', 0.5);

    % Legend with proper items
    legend_items = {'Dose with BG', 'Dose no BG', 'Dose CD'};
    if any(Dose_ROI_mask_all > 0)
        legend_items{end+1} = 'Dose lead';
    endif
    legend_items{end+1} = 'Avg coeff_bg * CD';
    legend_items{end+1} = 'Avg coeff * CD';

    legend_handles = [h1_plot, h2_plot, h3_plot];
    if any(Dose_ROI_mask_all > 0)
        legend_handles = [legend_handles, h4_plot];
    endif
    legend_handles = [legend_handles, h5_plot, h6_plot];

    legend(legend_handles, legend_items, 'Location', 'north', 'FontSize', 7, 'Box', 'on', 'EdgeColor', [0.5 0.5 0.5], 'Orientation', 'horizontal', 'Interpreter', 'none');

    % 2. Measurements Table
    n_rows = length(film_names) + 1;
    row_height = 0.035;
    table_content_height = row_height * n_rows;
    title_height = 0.025;
    plot_bottom = 0.74;
    gap_size = 0.05;
    table_title_top = plot_bottom - gap_size;
    table_title_bottom = table_title_top - title_height;
    table_bottom = table_title_bottom - table_content_height;

    subplot('Position', [0.05 table_bottom 0.9 table_content_height]);
    axis off;
    hold on;
    xlim([0 1]);
    ylim([0 1]);

    title_y_pos = 1 + (title_height / table_content_height);
    text(0.5, title_y_pos, 'Summary Table', 'FontSize', 10, 'FontWeight', 'bold', 'HorizontalAlignment', 'center', 'VerticalAlignment', 'middle');

    headers = {'File', 'Dose w/BG', 'Dose no BG', 'Dose CD', 'Dose lead', 'Charge', 'Notes', 'x0', 'y0', 'xstd', 'ystd'};

    rows = length(film_names);
    cols = length(headers);

    % Compose data for table
    table_data = cell(rows + 1, cols);
    table_data(1, :) = headers;
    for i = 1:rows
        if any(Dose_ROI_mask_all > 0)
            roi_dose_str = sprintf('%.2f ± %.2f', Dose_ROI_mask_all(i), Dose_ROI_mask_std_all(i));
        else
            roi_dose_str = 'N/A';
        endif

        table_data(i+1, :) = {
            film_names{i}(1:end-4), ...
            sprintf('%.2f ± %.2f', Dose_with_BGND_Gy_all(i), Dose_with_BGND_Gy_std_all(i)), ...
            sprintf('%.2f ± %.2f', Dose_Gy_all(i), Dose_Gy_std_all(i)), ...
            sprintf('%.2f ± %.2f', Dose_CD_all(i), Dose_CD_std_all(i)), ...
            roi_dose_str, ...
            sprintf('%.2f', chargeAll(i)), ...
            film_notes{i}, ...
            sprintf('%.2f', x0_all(i)), ...
            sprintf('%.2f', y0_all(i)), ...
            sprintf('%.2f', xstd_all(i)), ...
            sprintf('%.2f', ystd_all(i))
        };
    endfor

    % Compute column widths
    col_lengths = zeros(1, cols);
    for c = 1:cols
        max_len = 0;
        for r = 1:(rows+1)
            current_len = length(table_data{r, c});
            if r == 1
                current_len = current_len * 1.3;
            endif
            if c > 1 && r > 1
                current_len = current_len * 1.1;
            endif
            max_len = max(max_len, current_len);
        endfor
        col_lengths(c) = max_len;
    endfor

    min_widths = [6.1, 7.5, 7.5, 7.5, 7.5, 6.5, 7.2, 7.1, 7.1, 7, 7];
    col_lengths = max(col_lengths, min_widths);
    total_len = sum(col_lengths);
    col_norm = col_lengths / total_len;
    col_pos = [0, cumsum(col_norm)];

    norm_row_height = 1 / (rows + 1);

    % Draw table
    for r = 1:(rows + 1)
        current_y = 1 - (r-1) * norm_row_height;
        next_y = current_y - norm_row_height;

        line([0, 1], [current_y, current_y], 'Color', [0.3 0.3 0.3], 'LineWidth', 1.0);

        if r == (rows + 1)
            line([0, 1], [next_y, next_y], 'Color', [0.3 0.3 0.3], 'LineWidth', 1.0);
        endif

        for c = 1:cols
            x = col_pos(c);
            w = col_norm(c);
            val = table_data{r, c};

            line([x, x], [current_y, next_y], 'Color', [0.3 0.3 0.3], 'LineWidth', 1.0);
            if c == cols
                line([x + w, x + w], [current_y, next_y], 'Color', [0.3 0.3 0.3], 'LineWidth', 1.0);
            endif

            if r == 1
                fw = 'bold';
                font_size = 9;
            else
                fw = 'normal';
                font_size = 8.5;
            endif

            text_x = x + 0.008;
            text_y = current_y - norm_row_height/2;
            text(text_x, text_y, val, 'FontSize', font_size, ...
                 'FontWeight', fw, 'Interpreter', 'none', 'VerticalAlignment', 'middle', 'HorizontalAlignment', 'left');
        endfor
    endfor

    print(outfile, '-dpdf');

    % --- PAGE 2: Parameters and Calibration ---
    figure('visible', 'off', 'PaperUnits', 'centimeters', ...
           'PaperSize', [21 29.7], 'PaperPosition', [0.5 0.5 20 28.7]);

    % 1. Calibration Plot (if requested)
    if include_calib_plot
        subplot('Position', [0.1 0.82 0.8 0.15]);
        hold on;
        plot(x_vals, calibration_ratios1, '-x', 'linewidth', 1.3, ...
             'color', [0.5 0 0.8], 'markersize', 3, 'markeredgecolor', [0.5 0 0.8], 'markerfacecolor', 'none');
        plot(x_vals, calibration_ratios2, '-x', 'linewidth', 1.3, ...
             'color', [1 0.6 0.8], 'markersize', 3, 'markeredgecolor', [1 0.6 0.8], 'markerfacecolor', 'none');

        line([0.5, n + 0.5], [avg_calibration_coeff1, avg_calibration_coeff1], 'Color', [0.5 0.5 0.5], 'LineStyle', '--', 'LineWidth', 1.2);
        line([0.5, n + 0.5], [avg_calibration_coeff2, avg_calibration_coeff2], 'Color', [0.5 0.5 0.5], 'LineStyle', '-.', 'LineWidth', 1.2);

        xlim([0.5, n + 0.5]);
        xticks(x_vals);
        xlabel('Film #', 'FontSize', 9);
        ylabel('Coeff.', 'FontSize', 9);
        title('Calibration Coefficients', 'FontSize', 10);
        grid on;
        set(gca, 'FontSize', 8);

        legend({'Coeff_bg', 'Coeff', 'Avg Coeff_bg', 'Avg Coeff'}, 'Location', 'north', ...
               'FontSize', 7, 'Box', 'on', 'EdgeColor', [0.5 0.5 0.5], 'Orientation', 'horizontal', 'Interpreter', 'none');

        ax = gca;
        set(ax, 'XGrid', 'on', 'YGrid', 'on');
        set(ax, 'Layer', 'bottom');
        y_lims = ylim;
        x_lims = xlim;
        line([x_lims(1) x_lims(2)], [y_lims(2) y_lims(2)], 'Color', [0.15 0.15 0.15], 'LineWidth', 0.5);
        line([x_lims(2) x_lims(2)], [y_lims(1) y_lims(2)], 'Color', [0.15 0.15 0.15], 'LineWidth', 0.5);
    endif

    % 2. Analysis Parameters Section
    subplot('Position', [0.1 0.12 0.8 0.65]);
    axis off;
    hold on;
    xlim([0 1]);
    ylim([0 1]);

    y_pos = 0.95;
    line_spacing = 0.06;

    text(0.5, y_pos, 'Analysis Parameters', 'FontSize', 14, 'FontWeight', 'bold', 'HorizontalAlignment', 'center');
    y_pos = y_pos - line_spacing;

    if strcmp(roi_shape, "circle")
        roi_text = sprintf('ROI: circle, Radius (mm): %.1f', roi_size);
    else
        roi_text = sprintf('ROI: square, Side length (mm): %.1f', 2*roi_size);
    endif
    text(0.1, y_pos, roi_text, 'FontSize', 12, 'FontWeight', 'bold');
    y_pos = y_pos - line_spacing;

    if strcmp(bgnd_choice, "edge")
        bgnd_text = 'Background Type: edge-based';
    else
        bgnd_text = sprintf('Background Type: %s', bgnd_file);
    endif
    text(0.1, y_pos, bgnd_text, 'FontSize', 12, 'FontWeight', 'bold', 'Interpreter', 'none');
    y_pos = y_pos - line_spacing;

    % Calculate percentage deviations
    percent_dev1 = (std_calibration_coeff1 / avg_calibration_coeff1) * 100;
    percent_dev2 = (std_calibration_coeff2 / avg_calibration_coeff2) * 100;

    calib_text1 = sprintf('Calibration Coefficient (average w/BG): %.3f ± %.3f (%.1f%%)', avg_calibration_coeff1, std_calibration_coeff1, percent_dev1);
    text(0.1, y_pos, calib_text1, 'FontSize', 12, 'FontWeight', 'bold');
    y_pos = y_pos - line_spacing;

    calib_text2 = sprintf('Calibration Coefficient (average no BG): %.3f ± %.3f (%.1f%%)', avg_calibration_coeff2, std_calibration_coeff2, percent_dev2);
    text(0.1, y_pos, calib_text2, 'FontSize', 12, 'FontWeight', 'bold');
    y_pos = y_pos - line_spacing;

    % ROI Image Display
    if ~isempty(roi_image_path)
        combined_text = 'Image of the lead films';
        if ~isempty(selected_masks)
            mask_numbers = '';
            for i = 1:length(selected_masks)
                if i == 1
                    mask_numbers = [mask_numbers sprintf('%d', selected_masks(i))];
                else
                    mask_numbers = [mask_numbers sprintf(', %d', selected_masks(i))];
                endif
            endfor
            combined_text = [combined_text ' (selected masks: ' mask_numbers ')'];
        endif

        text(0.1, y_pos, combined_text, 'FontSize', 12, 'FontWeight', 'bold');
        text_end_position = y_pos;
        y_pos = y_pos - line_spacing;

        % Display ROI image with original positioning
        roi_img = imread(roi_image_path);
        [img_height_px, img_width_px, ~] = size(roi_img);
        aspect_ratio = img_width_px / img_height_px;
        max_img_height = 0.95;
        max_img_width = 0.99;

        if aspect_ratio > (max_img_width / max_img_height)
            img_width_norm = max_img_width;
            img_height_norm = max_img_width / aspect_ratio;
        else
            img_height_norm = max_img_height;
            img_width_norm = max_img_height * aspect_ratio;
        endif

        img_x = 0.04 + (0.99 - img_width_norm) / 2;
        img_y = 0.69 - (0.95 - text_end_position) * 0.1 - img_height_norm;

        img_axes = axes('Position', [img_x img_y img_width_norm img_height_norm]);
        set(img_axes, 'LooseInset', [0 0 0 0]);

        if size(roi_img, 3) == 3
            if isa(roi_img, 'uint8')
                roi_img_display = double(roi_img) / 255;
            else
                roi_img_display = double(roi_img);
            endif
            imagesc(roi_img_display);
        elseif size(roi_img, 3) == 1
            if isa(roi_img, 'uint8')
                roi_img_display = double(roi_img);
            else
                roi_img_display = double(roi_img);
            endif
            imagesc(roi_img_display);
            colormap(img_axes, gray(256));
        endif

        axis equal;
        axis tight;
        axis off;
        set(img_axes, 'XTick', [], 'YTick', [], 'Box', 'off');
        set(img_axes, 'DataAspectRatio', [1 1 1]);
    endif

    print(outfile, '-dpdf', '-append');

    % --- PAGE 3: Position and Size Jitter ---
    figure('visible', 'off', 'PaperUnits', 'centimeters', 'PaperSize', [21 29.7], 'PaperPosition', [0.5 0.5 20 28.7]);

    % 1. Size Jitter Plot
    subplot('Position', [0.1 0.82 0.8 0.15]);
    hold on;
    plot(x_vals, xstd_all, '-*', 'color', [0.2 0.4 0.8], 'markerfacecolor', [0.2 0.4 0.8], 'linewidth', 1.2, 'markersize', 3.5);
    plot(x_vals, ystd_all, '-*', 'color', [0.8 0.2 0.2], 'markerfacecolor', [0.8 0.2 0.2], 'linewidth', 1.2, 'markersize', 3.5);

    xlim([0.5, n + 0.5]);
    xticks(x_vals);
    xlabel('Film #', 'FontSize', 9);
    ylabel('Size [mm]', 'FontSize', 9);
    title('Size Jitter', 'FontSize', 10);
    grid on;
    line([xlim()(2) xlim()(2)], ylim(), 'Color', [0.15 0.15 0.15], 'LineWidth', 0.5);
    legend({'xstd', 'ystd'}, 'Location', 'north', 'Orientation', 'horizontal', 'FontSize', 8);

    % 2. Position Jitter Plot
    subplot('Position', [0.1 0.60 0.8 0.15]);
    hold on;
    plot(x_vals, x0_all, '-*', 'color', [0.2 0.4 0.8], 'markerfacecolor', [0.2 0.4 0.8], 'linewidth', 1.2, 'markersize', 3.5);
    plot(x_vals, y0_all, '-*', 'color', [0.8 0.2 0.2], 'markerfacecolor', [0.8 0.2 0.2], 'linewidth', 1.2, 'markersize', 3.5);

    xlim([0.5, n + 0.5]);
    xticks(x_vals);
    xlabel('Film #', 'FontSize', 9);
    ylabel('Position [mm]', 'FontSize', 9);
    title('Position Jitter', 'FontSize', 10);
    grid on;
    line([xlim()(2) xlim()(2)], ylim(), 'Color', [0.15 0.15 0.15], 'LineWidth', 0.5);
    legend({'x0', 'y0'}, 'Location', 'north', 'Orientation', 'horizontal', 'FontSize', 8);

    print(outfile, '-dpdf', '-append');

    % Cleanup
    printf("PDF report saved to %s.pdf\n", outfile);
    graphics_toolkit(current_toolkit);
    close all force;
end
