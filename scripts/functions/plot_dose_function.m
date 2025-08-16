function [Dose_center, xstd, ystd, x0, y0, bgnd_Dose_x, bgnd_Dose_y, Dose_center_std] = plot_dose_function(Dose, name_output, pixsizeX, pixsizeY, roi_size, npix, T_calibration, roi_shape)

pkg load optim
warning('off', 'Octave:shadowed-function');

global calibration charge_calibration name_screen

sizeall = size(Dose);
ny = sizeall(1);
nx = sizeall(2);

% Create coordinate arrays with geometric center as origin
center_x = (nx - 1) * pixsizeX / 2;
center_y = (ny - 1) * pixsizeY / 2;

x = ((0:nx-1) * pixsizeX) - center_x;
y = ((0:ny-1) * pixsizeY) - center_y;

% Normalize image and calculate projections
Total = sum(Dose(:));
imageN = Dose / Total;

projX = sum(imageN, 1);
projY = sum(imageN, 2).';

% Calculate centroid and standard deviations
x0 = sum(projX .* x) / sum(projX);
y0 = sum(projY .* y) / sum(projY);
xstd = sqrt(sum(projX .* ((x - x0).^2)) / sum(projX));
ystd = sqrt(sum(projY .* ((y - y0).^2)) / sum(projY));

% Convert to pixel coordinates for array indexing
pix_x0 = round((x0 + center_x) / pixsizeX);
pix_y0 = round((y0 + center_y) / pixsizeY);

[XX, YY] = meshgrid(x, y);
dpix = round(roi_size / pixsizeX);

% Calculate dose in ROI region
if strcmp(roi_shape, "circle")
    circlePixels = (YY - y0).^2 + (XX - x0).^2 <= roi_size.^2;
    dose_values_in_region = Dose(circlePixels);
    Dose_center = mean(dose_values_in_region);
    Dose_center_std = std(dose_values_in_region);
    region_desc = strcat(" circle (r=", num2str(roi_size), " mm)");
else
    dose_values_in_region = Dose(pix_y0-dpix:pix_y0+dpix, pix_x0-dpix:pix_x0+dpix);
    Dose_center = mean(dose_values_in_region(:));
    Dose_center_std = std(dose_values_in_region(:));
    region_desc = strcat(" square (side=", num2str(2*roi_size), " mm)");
endif

Dose_center_no_calibration = Dose_center;

% Calculate dose projections for fitting
projDX = mean(Dose, 1);
projDY = mean(Dose, 2).';

% Create circle points for plotting
p = linspace(0, 2*pi, 100);

% Gaussian fitting function
f = @(param, x) param(1) * exp(-(x-param(2)).^2/(2*param(3)^2)) + param(4);

% Fit Gaussian to projections
[param] = nonlin_curvefit(f, [1.0; 1.0; 1.0; 0.0], x-x0, projX);
sigma_x = param(3);
GaussX = param(1) * exp(-(x-x0-param(2)).^2/(2*param(3)^2)) + param(4);
offset_fit_x = param(4);

[param] = nonlin_curvefit(f, [1.0; 1.0; 1.0; 0.0], y-y0, projY);
sigma_y = param(3);
GaussY = param(1) * exp(-(y-y0-param(2)).^2/(2*param(3)^2)) + param(4);
offset_fit_y = param(4);

% Fit dose slices
xslice = T_calibration * mean(Dose(pix_y0-npix/2:pix_y0+npix/2, :));
[param] = nonlin_curvefit(f, [18.0; 1.0; 1.0; 0.0], x-x0, xslice);
bgnd_Dose_x = param(4);
GaussXS = param(1) * exp(-(x-x0-param(2)).^2/(2*param(3)^2)) + param(4);

yslice = mean(Dose(:, pix_x0-npix/2:pix_x0+npix/2), 2).';
[param] = nonlin_curvefit(f, [18.0; 1.0; 1.0; 0.0], y-y0, yslice);
bgnd_Dose_y = param(4);
GaussYS = param(1) * exp(-(y-y0-param(2)).^2/(2*param(3)^2)) + param(4);

% Create plots
clf;
figure(1, 'visible', 'off', 'position', [20, 400, 1350, 800]);

% Dose map plot
subplot(3, 1, 1);
imagesc(x, y, flipud(Dose*calibration));
set(gca, 'YDir', 'normal');
colorbar;
title(strcat("Dose map in Gy, Dose in the center ", region_desc, "=", num2str(Dose_center*T_calibration), " Gy"), 'fontsize', 10);
xlabel('x [mm]');
ylabel('y [mm]');
axis equal;
hold on;
y0_display = -y0;
plot(x0, y0_display, 'r+');

% Draw ROI shape
if strcmp(roi_shape, "circle")
    plot(x0+roi_size*cos(p), y0_display+roi_size*sin(p), 'r--');
else
    square_x = [x0-roi_size, x0+roi_size, x0+roi_size, x0-roi_size, x0-roi_size];
    square_y = [y0_display-roi_size, y0_display-roi_size, y0_display+roi_size, y0_display+roi_size, y0_display-roi_size];
    plot(square_x, square_y, 'r--');
endif

% Projections plot
subplot(3, 1, 2);
tits1 = strcat('Projections, RMS//FIT values: {\sigma}_x=', num2str(xstd), '//', num2str(sigma_x), ' mm, {\sigma}_y=', num2str(ystd), '//', num2str(sigma_y), " mm");
plot(x-x0, projX);
title(tits1);
xlabel('coordinate [mm]');
ylabel('projection [arb.units.]');
hold on;
plot(y-y0, projY);
plot(x-x0, GaussX, 'b:');
plot(y-y0, GaussY, 'r:');
legend('x', 'y', 'x-G', 'y-G', 'location', 'eastoutside');

% Average profiles plot
subplot(3, 1, 3);
tits2 = strcat('Average profile over several central slices, bgnd x//y values:', num2str(bgnd_Dose_x), '//', num2str(bgnd_Dose_y), ' Gy');
plot(x-x0, T_calibration*mean(Dose(pix_x0-npix/2:pix_x0+npix/2, :)));
title(tits2);
xlabel('coordinate [mm]');
ylabel(strcat(num2str(npix), '-slice-mean dose [Gy]'));
hold on;
plot(y-y0, T_calibration*mean(Dose(:, pix_y0-npix/2:pix_y0+npix/2), 2));
plot(x-x0, GaussXS, 'b:');
plot(y-y0, GaussYS, 'r:');
line([min(x-x0) max(x-x0)], [Dose_center*T_calibration Dose_center*T_calibration], "linestyle", "--", "color", "k");
legend('x', 'y', 'x-G', 'y-G', 'Dose center', 'location', 'eastoutside');

% Create images directory and save
if ~exist("images", "dir")
    mkdir("images");
endif

saveas(gcf, strcat('images/', name_output, '.png'));

% Apply calibration to final results
Dose_center = Dose_center * T_calibration;
Dose_center_std = Dose_center_std * T_calibration;

end
