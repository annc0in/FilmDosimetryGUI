function [Dose_center_mask, Dose_center_mask_std] = calculate_roi_mask_dose(Dose_Film, roi_mat_path, selected_mask_numbers, DownCut, UpCut, LeftCut, RightCut)
% Calculate mean dose within ROI mask regions

    load(roi_mat_path, 'lead_data');
    [ny, nx] = size(Dose_Film);

    if length(selected_mask_numbers) == 1
        % Single mask processing
        mask_num = selected_mask_numbers(1);
        field_name = sprintf('film_%d', mask_num);

        if isfield(lead_data, field_name)
            mask_coords = lead_data.(field_name).mask_pixel_coords;

            % Adjust coordinates for image cropping
            adjusted_coords = mask_coords;
            adjusted_coords(:,1) = adjusted_coords(:,1) - DownCut;
            adjusted_coords(:,2) = adjusted_coords(:,2) - LeftCut;

            % Keep valid coordinates within image bounds
            valid_coords = (adjusted_coords(:,1) >= 1) & (adjusted_coords(:,1) <= ny) & ...
                          (adjusted_coords(:,2) >= 1) & (adjusted_coords(:,2) <= nx);
            adjusted_coords = adjusted_coords(valid_coords, :);

            if ~isempty(adjusted_coords)
                linear_indices = sub2ind([ny, nx], adjusted_coords(:,1), adjusted_coords(:,2));
                dose_values_in_mask = Dose_Film(linear_indices);
                Dose_center_mask = mean(dose_values_in_mask);
                Dose_center_mask_std = std(dose_values_in_mask);
            else
                Dose_center_mask = 0;
                Dose_center_mask_std = 0;
            endif
        else
            Dose_center_mask = 0;
            Dose_center_mask_std = 0;
        endif

    else
        % Multiple masks - find intersection
        intersection_mask = true(ny, nx);
        masks_found = 0;

        for mask_num = selected_mask_numbers
            field_name = sprintf('film_%d', mask_num);

            if isfield(lead_data, field_name)
                masks_found = masks_found + 1;
                mask_coords = lead_data.(field_name).mask_pixel_coords;

                adjusted_coords = mask_coords;
                adjusted_coords(:,1) = adjusted_coords(:,1) - DownCut;
                adjusted_coords(:,2) = adjusted_coords(:,2) - LeftCut;

                valid_coords = (adjusted_coords(:,1) >= 1) & (adjusted_coords(:,1) <= ny) & ...
                              (adjusted_coords(:,2) >= 1) & (adjusted_coords(:,2) <= nx);
                adjusted_coords = adjusted_coords(valid_coords, :);

                current_mask = false(ny, nx);
                if ~isempty(adjusted_coords)
                    linear_indices = sub2ind([ny, nx], adjusted_coords(:,1), adjusted_coords(:,2));
                    current_mask(linear_indices) = true;
                endif

                intersection_mask = intersection_mask & current_mask;
            endif
        endfor

        if masks_found > 0 && any(intersection_mask(:))
            dose_values_in_intersection = Dose_Film(intersection_mask);
            Dose_center_mask = mean(dose_values_in_intersection);
            Dose_center_mask_std = std(dose_values_in_intersection);
        else
            Dose_center_mask = 0;
            Dose_center_mask_std = 0;
        endif
    endif
end
