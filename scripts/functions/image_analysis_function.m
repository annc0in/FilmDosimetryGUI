function [Dose_Film, Dose_Film_nobgnd, Dose_Gauss, Dose_Exp_EBT3, Dose_Exp_XDWrong, nxF, nyF, nx, ny] = ...
    image_analysis_function(imageF, charge, imageBGND_F, BGND_Type, DownCut, UpCut, LeftCut, RightCut, pixsizeX, pixsizeY)

charge

% Get image dimensions
sizeall = size(imageF);
nyF = sizeall(1);
nxF = sizeall(2);

% Crop image to analysis region
image = imageF(DownCut:nyF-UpCut, LeftCut:nxF-RightCut);
Dose_Film = image;
sizeall = size(image);
ny = sizeall(1);
nx = sizeall(2);

Dose_Gauss = zeros(sizeall);

% Background subtraction
if (BGND_Type == 0)
    % Use pre-recorded background image
    imageBGND = imageBGND_F(DownCut:nyF-UpCut, LeftCut:nxF-RightCut);

    total_pix_BGND = sum(imageBGND(:));
    total_pix = sum(image(:));
    Ratio = total_pix_BGND / total_pix;

    printf("Total pre-recorded background to image: %d%%\n", round(Ratio*100));

    image = image - imageBGND;
    Dose_Film_nobgnd = image;
else
    % Use edge-based background estimation
    dn = BGND_Type; % Number of edge slices

    % Calculate background from image edges
    a1 = mean(mean(image(:, nx-dn:nx))); % Right edge
    a2 = mean(mean(image(:, 1:1+dn))); % Left edge
    a3 = mean(mean(image(ny-dn:ny, :))); % Bottom edge
    a4 = mean(mean(image(1:1+dn, :))); % Top edge

    a = [a1, a2, a3, a4];
    bgnd = mean(a);
    bgnd_std = std(a);

    imageC = image - bgnd;
    total_pix = sum(image(:));
    imageBGND_FLAT = image - imageC;
    total_pix_BGND = sum(imageBGND_FLAT(:));
    Ratio = total_pix_BGND / total_pix;
    image = imageC;
    Dose_Film_nobgnd = image;

    printf("Background standard deviation to mean in edges: %d%%\n", round(bgnd_std/bgnd*100));
    printf("Total background to image from edges: %d%%\n", round(Ratio*100));
end

% Normalize image to total charge
total_pix = sum(image(:));
imageN = double(image / total_pix);

% Scale by charge measurement
imageNC = imageN * charge;
totalCharge_nC = sum(imageNC(:));
printf("Total charge check: %.3f nC\n", totalCharge_nC);

% Calculate charge density
pixel_area = pixsizeY * pixsizeX;
Density2D = imageNC / pixel_area;

% Calculate doses for different calibrations
coeff = (3.27+3.45)/3.1921*9.8/(4.0+4.0); % XD films coefficient
k = (5.5^2);
Dose_Exp_XDWrong = Density2D * k * coeff;

coeff_EBT3 = 1;
Dose_Exp_EBT3 = Density2D * coeff_EBT3;

% Gaussian dose calculation
Dose_1Gy = 1;
totalCharge_nC = 1;
sigmaX = 5.5;

Density2D0 = totalCharge_nC / (2*pi*sigmaX^2);
coeff_theory = Dose_1Gy / Density2D0;

Dose_Gauss = Density2D * coeff_theory;

end
