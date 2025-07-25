
from astropy.io import fits
from photutils.psf import fit_fwhm
from photutils.detection import DAOStarFinder
from photutils.centroids import centroid_1dg, centroid_2dg, centroid_com, centroid_quadratic
from astropy.stats import SigmaClip, sigma_clipped_stats
from photutils.segmentation import detect_threshold, detect_sources
from photutils.utils import circular_footprint

import numpy as np
import matplotlib.pyplot as plt
import argparse


def photometry(fits_file, est_fwhm=10, verbose=False):
    if verbose:
        plt.ion()
    
    try: 
        hdu = fits.open(fits_file)
        data = hdu[0].data
    except FileNotFoundError:
        raise FileNotFoundError(f"File {fits_file} not found.")
    except Exception as e:
        raise Exception(f"Error occurred while opening {fits_file}: {e}")

    if verbose:
        print(hdu.info(), "\n")

    if verbose:
        max_index = np.argmax(data)
        y_max, x_max = np.unravel_index(max_index, data.shape)
        print(f"Brightest pixel at position: x={x_max}, y={y_max}, value={data[y_max, x_max]}")
        
    sigma_clip = SigmaClip(sigma=3.0, maxiters=10)
    threshold = detect_threshold(data, nsigma=5.0, sigma_clip=sigma_clip)
    segment_img = detect_sources(data, threshold, npixels=10)
    if segment_img is None:
        raise ValueError("No sources detected in the image.")
    footprint = circular_footprint(radius=int(est_fwhm))
    mask = segment_img.make_source_mask(footprint=footprint)
    mean, median, std = sigma_clipped_stats(data, sigma=3.0, mask=mask)

    if verbose:
        print(f"Mean: {mean}, Median: {median}, Std: {std}")

    # background = data.copy()
    # background[mask] = median

    data = data - median
    

    sources = DAOStarFinder(100, est_fwhm).find_stars(data)
    sources.sort('flux', reverse=True)
    focus_star = sources[0]
    if verbose: 
        print(focus_star, "\n")

    region_size = est_fwhm * 3
    y_min = int(max(0, focus_star['ycentroid'] - region_size//2))
    y_max = int(min(data.shape[0], focus_star['ycentroid'] + region_size//2))
    x_min = int(max(0, focus_star['xcentroid'] - region_size//2))
    x_max = int(min(data.shape[1], focus_star['xcentroid'] + region_size//2))
    data = data[y_min:y_max, x_min:x_max]

    xcent, ycent = centroid_2dg(data)

    if verbose:
        plt.figure(figsize=(8, 8))
        plt.imshow(data, origin='lower', cmap='grey')
        plt.plot(xcent, ycent, 'r+', markersize=10)
        plt.annotate('Centroid', (xcent, ycent), xytext=(5, 5), textcoords='offset points', color='white')
        plt.show()
        # plt.savefig('psf-practice/cutout.png')


    fit_x = data.shape[0]
    fit_y = data.shape[1]
    if fit_x%2 == 0:
        fit_x -= 1
    if fit_y%2 == 0:
        fit_y -= 1
    fit_shape = (fit_x, fit_y)

    
    est_fwhm = fit_fwhm(data, fit_shape=fit_shape)
    # est_fwhm.sort()
    # est_fwhm = est_fwhm[-1]
    print(f"Estimated FWHM: {est_fwhm}")

    x = np.arange(data.shape[1])
    y = np.arange(data.shape[0])

    meshgrid_x, meshgrid_y = np.meshgrid(x, y)

    M1_x = np.sum(meshgrid_x * data) / np.sum(data)
    M1_y = np.sum(meshgrid_y * data) / np.sum(data)

    M2_x = np.sum((meshgrid_x)** 2 * data) / np.sum(data)
    M2_y = np.sum((meshgrid_y)** 2 * data) / np.sum(data)

    sigma_x = np.sqrt(M2_x - M1_x**2)
    sigma_y = np.sqrt(M2_y - M1_y**2)

    FWHM_x = 2 * np.sqrt(2 * np.log(2)) * sigma_x
    FWHM_y = 2 * np.sqrt(2 * np.log(2)) * sigma_y
    average_FWHM = (FWHM_x + FWHM_y) / 2

    if verbose:
        print(f"FWHM_x: {FWHM_x}, FWHM_y: {FWHM_y}, Average FWHM: {average_FWHM}")

    if verbose:
        plt.ioff()
        input("Press Enter to exit...")

    return average_FWHM


import numpy as np
import matplotlib.pyplot as plt
import argparse


# if __name__ == "__main__":
#     main()