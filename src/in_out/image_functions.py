import os.path
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + os.path.sep + '../../../')

import numpy as np


def points_to_voxels_transform(points, affine):
    """
    Only useful for image + mesh cases. Not implemented yet.
    """
    return points


def metric_to_image_radial_length(length, affine):
    """
        Only useful for image + mesh cases. Not implemented yet.
        """
    return length


def normalize_image_intensities(intensities):

    dtype = str(intensities.dtype)
    assert dtype in ['uint8', 'uint16', 'uint32', 'uint64', 'float8','float16', 'float32', 'float64'], \
        ('Error: the image intensities dtype = %s is not managed for now. Ask the Deformetrica team to add it for you!'
         % dtype)

    if dtype in ['uint8', 'float8']:
        return (intensities.astype('uint8') / 255.0), dtype

    elif dtype in ['uint16', 'float16']:
        return (intensities.astype('uint16') / 65535.0), dtype

    elif dtype in ['uint32', 'float32']:
        return (intensities.astype('uint32') / 4294967295.0), dtype

    elif dtype in ['uint64', 'float64']:
        return (intensities.astype('uint64') / 18446744073709551615.0), dtype


def rescale_image_intensities(intensities, dtype):
    tol = 1e-10

    assert dtype in ['uint8', 'uint16', 'uint32', 'uint64', 'float8', 'float16', 'float32', 'float64'], \
        ('Error: the image intensities dtype = %s is not managed for now. Ask the Deformetrica team to add it for you!'
         % dtype)

    if dtype in ['uint8', 'float8']:
        return (np.clip(intensities, tol, 1 - tol) * 255).astype('uint8')

    elif dtype in ['uint16', 'float16']:
        return (np.clip(intensities, tol, 1 - tol) * 65535).astype('uint16')

    elif dtype in ['uint32', 'float32']:
        return (np.clip(intensities, tol, 1 - tol) * 4294967295).astype('uint32')

    elif dtype in ['uint64', 'float64']:
        return (np.clip(intensities, tol, 1 - tol) * 18446744073709551615).astype('uint64')
