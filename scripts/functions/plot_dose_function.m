function [Dose_center, xstd, ystd, x0, y0, bgnd_Dose_x, bgnd_Dose_y, Dose_center_std] = ...
         plot_dose_function(Dose, name_output, pixsizeX, pixsizeY, roi_size, npix, T_calibration, roi_shape)

global calibration charge_calibration name_screen

sizeall = size(Dose);
ny = sizeall(1);
nx = sizeall(2);

% Coordinates centered
center_x = (nx - 1) * pixsizeX / 2;
center_y = (ny - 1) * pixsizeY / 2;
x = ((0:nx-1) * pixsizeX) - center_x;
y = ((0:ny-1) * pixsizeY) - center_y;

% Normalize image and projections
Total = sum(Dose(:));
imageN = Dose / Total;
projX = sum(imageN, 1);
projY = sum(imageN, 2).';

% Centroid and RMS
x0 = sum(projX .* x) / sum(projX);
y0 = sum(projY .* y) / sum(projY);
xstd = sqrt(sum(projX .* ((x - x0).^2)) / sum(projX));
ystd = sqrt(sum(projY .* ((y - y0).^2)) / sum(projY));

% Pixel coordinates
pix_x0 = round((x0 + center_x) / pixsizeX);
pix_y0 = round((y0 + center_y) / pixsizeY);
[XX, YY] = meshgrid(x, y);
dpix = round(roi_size / pixsizeX);

% ROI dose
if strcmp(roi_shape, "circle")
    circlePixels = (YY - y0).^2 + (XX - x0).^2 <= roi_size.^2;
    vals = Dose(circlePixels);
    Dose_center = mean(vals);
    Dose_center_std = std(vals);
    region_desc = strcat(" circle (r=", num2str(roi_size), " mm)");
else
    vals = Dose(pix_y0-dpix:pix_y0+dpix, pix_x0-dpix:pix_x0+dpix);
    Dose_center = mean(vals(:));
    Dose_center_std = std(vals(:));
    region_desc = strcat(" square (side=", num2str(2*roi_size), " mm)");
endif

Dose_center_no_calibration = Dose_center;

% Gaussian model
f = @(param, x) param(1) * exp(-(x-param(2)).^2/(2*param(3)^2)) + param(4);

% Inline deterministic Gaussian fitting
fit_gaussian = @(init_param, xv, yv) ...
    fminsearch(@(p) sum((f(p, xv) - yv).^2), init_param, optimset('TolX',1e-8,'TolFun',1e-8,'MaxIter',1e4,'MaxFunEvals',1e4,'Display','off'));

% Fit projections
param = fit_gaussian([1.0;1.0;1.0;0.0], x-x0, projX);
sigma_x = param(3);
GaussX = f(param, x-x0);

param = fit_gaussian([1.0;1.0;1.0;0.0], y-y0, projY);
sigma_y = param(3);
GaussY = f(param, y-y0);

% Fit central slices
xslice = T_calibration * mean(Dose(pix_y0-npix/2:pix_y0+npix/2, :));
param = fit_gaussian([18.0;1.0;1.0;0.0], x-x0, xslice);
bgnd_Dose_x = param(4);
GaussXS = f(param, x-x0);

yslice = mean(Dose(:, pix_x0-npix/2:pix_x0+npix/2), 2).';
param = fit_gaussian([18.0;1.0;1.0;0.0], y-y0, yslice);
bgnd_Dose_y = param(4);
GaussYS = f(param, y-y0);

% Plots
clf;
figure(1, 'visible', 'off', 'position', [20,400,1350,800]);

% Dose map
subplot(3,1,1);
imagesc(x,y,flipud(Dose*calibration));
set(gca,'YDir','normal'); colorbar;
title(strcat("Dose map in Gy, Dose in the center ", region_desc, "=", num2str(Dose_center*T_calibration), " Gy"), 'fontsize',10);
xlabel('x [mm]'); ylabel('y [mm]'); axis equal; hold on;
plot(x0,-y0,'r+');

if strcmp(roi_shape,"circle")
    p = linspace(0,2*pi,100);
    plot(x0+roi_size*cos(p), -y0+roi_size*sin(p),'r--');
else
    square_x = [x0-roi_size,x0+roi_size,x0+roi_size,x0-roi_size,x0-roi_size];
    square_y = [-y0-roi_size,-y0-roi_size,-y0+roi_size,-y0+roi_size,-y0-roi_size];
    plot(square_x,square_y,'r--');
endif

% Projections
subplot(3,1,2);
plot(x-x0, projX); hold on;
plot(y-y0, projY);
plot(x-x0, GaussX,'b:'); plot(y-y0, GaussY,'r:');
title(strcat('Projections, RMS//FIT: \sigma_x=', num2str(xstd),'//',num2str(sigma_x), ' mm, \sigma_y=', num2str(ystd),'//',num2str(sigma_y),' mm'));
xlabel('coordinate [mm]'); ylabel('projection [arb.units.]'); legend('x','y','x-G','y-G','location','eastoutside');

% Central slices
subplot(3,1,3);
plot(x-x0, xslice); hold on; plot(y-y0, T_calibration*mean(Dose(:, pix_y0-npix/2:pix_y0+npix/2),2));
plot(x-x0, GaussXS,'b:'); plot(y-y0, GaussYS,'r:');
line([min(x-x0) max(x-x0)], [Dose_center*T_calibration Dose_center*T_calibration],"linestyle","--","color","k");
title(strcat('Average profile, bgnd x//y:', num2str(bgnd_Dose_x),'//',num2str(bgnd_Dose_y),' Gy'));
xlabel('coordinate [mm]'); ylabel(strcat(num2str(npix),'-slice-mean dose [Gy]'));
legend('x','y','x-G','y-G','Dose center','location','eastoutside');

if ~exist("images","dir"); mkdir("images"); endif
saveas(gcf,strcat('images/',name_output,'.png'));

% Calibration
Dose_center = Dose_center*T_calibration;
Dose_center_std = Dose_center_std*T_calibration;

end

