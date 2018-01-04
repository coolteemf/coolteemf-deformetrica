import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + os.path.sep + '../../../')

import torch
from torch.autograd import Variable
import warnings
import time

from pydeformetrica.src.core.models.bayesian_atlas import BayesianAtlas
from pydeformetrica.src.core.estimators.torch_optimize import TorchOptimize
from pydeformetrica.src.core.estimators.scipy_optimize import ScipyOptimize
from pydeformetrica.src.core.estimators.gradient_ascent import GradientAscent
from pydeformetrica.src.core.estimators.mcmc_saem import McmcSaem
from pydeformetrica.src.support.utilities.general_settings import Settings
from pydeformetrica.src.support.kernels.kernel_functions import create_kernel
from pydeformetrica.src.in_out.dataset_functions import create_dataset
from src.in_out.utils import *


def estimate_bayesian_atlas(xml_parameters):
    print('[ estimate_bayesian_atlas function ]')
    print('')

    """
    Create the dataset object.
    """

    dataset = create_dataset(xml_parameters.dataset_filenames, xml_parameters.visit_ages,
                             xml_parameters.subject_ids, xml_parameters.template_specifications)

    assert (dataset.is_cross_sectional()), "Cannot estimate an atlas from a non-cross-sectional dataset."

    """
    Create the model object.
    """

    model = BayesianAtlas()

    model.diffeomorphism.kernel = create_kernel(xml_parameters.deformation_kernel_type,
                                                xml_parameters.deformation_kernel_width)
    model.diffeomorphism.number_of_time_points = xml_parameters.number_of_time_points
    model.diffeomorphism.set_use_rk2(xml_parameters.use_rk2)

    if not xml_parameters.initial_control_points is None:
        control_points = read_2D_array(xml_parameters.initial_control_points)
        model.set_control_points(control_points)

    if not xml_parameters.initial_momenta is None:
        momenta = read_momenta(xml_parameters.initial_momenta)
        model.set_momenta(momenta)

    model.freeze_template = xml_parameters.freeze_template  # this should happen before the init of the template and the cps
    model.freeze_control_points = xml_parameters.freeze_control_points

    model.initialize_template_attributes(xml_parameters.template_specifications)

    model.smoothing_kernel_width = xml_parameters.deformation_kernel_width * xml_parameters.sobolev_kernel_width_ratio
    model.initial_cp_spacing = xml_parameters.initial_cp_spacing
    model.number_of_subjects = dataset.number_of_subjects

    # Prior on the covariance momenta (inverse Wishart: degrees of freedom parameter).
    model.priors['covariance_momenta'].degrees_of_freedom = dataset.number_of_subjects \
                                                            * xml_parameters.covariance_momenta_prior_normalized_dof

    # Prior on the noise variance (inverse Wishart: degrees of freedom parameter).
    for k, object in enumerate(xml_parameters.template_specifications.values()):
        model.priors['noise_variance'].degrees_of_freedom.append(dataset.number_of_subjects
                                                                 * object['noise_variance_prior_normalized_dof']
                                                                 * model.objects_noise_dimension[k])

    model.update()

    """
    Create the estimator object.
    """

    if xml_parameters.optimization_method_type == 'GradientAscent'.lower():
        estimator = GradientAscent()
        estimator.initial_step_size = xml_parameters.initial_step_size
        estimator.max_line_search_iterations = xml_parameters.max_line_search_iterations
        estimator.line_search_shrink = xml_parameters.line_search_shrink
        estimator.line_search_expand = xml_parameters.line_search_expand

    elif xml_parameters.optimization_method_type == 'TorchLBFGS'.lower():
        if not model.freeze_template and model.use_sobolev_gradient:
            model.use_sobolev_gradient = False
            msg = 'Impossible to use a Sobolev gradient for the template data with the TorchLBFGS estimator. ' \
                  'Overriding the "use_sobolev_gradient" option, now set to "off".'
            warnings.warn(msg)
        estimator = TorchOptimize()

    elif xml_parameters.optimization_method_type == 'ScipyLBFGS'.lower():
        estimator = ScipyOptimize()
        estimator.memory_length = xml_parameters.memory_length
        if not model.freeze_template and model.use_sobolev_gradient and estimator.memory_length > 1:
            estimator.memory_length = 1
            msg = 'Impossible to use a Sobolev gradient for the template data with the ScipyLBFGS estimator memory ' \
                  'length being larger than 1. Overriding the "memory_length" option, now set to "1".'
            warnings.warn(msg)

    elif xml_parameters.optimization_method_type == 'McmcSaem'.lower():
        estimator = McmcSaem()

    else:
        estimator = GradientAscent()
        estimator.initial_step_size = xml_parameters.initial_step_size
        estimator.max_line_search_iterations = xml_parameters.max_line_search_iterations
        estimator.line_search_shrink = xml_parameters.line_search_shrink
        estimator.line_search_expand = xml_parameters.line_search_expand

        msg = 'Unknown optimization-method-type: \"' + xml_parameters.optimization_method_type \
              + '\". Defaulting to GradientAscent.'
        warnings.warn(msg)

    estimator.max_iterations = xml_parameters.max_iterations
    estimator.convergence_tolerance = xml_parameters.convergence_tolerance

    estimator.print_every_n_iters = xml_parameters.print_every_n_iters
    estimator.save_every_n_iters = xml_parameters.save_every_n_iters

    estimator.dataset = dataset
    estimator.statistical_model = model

    # Initial random effects realizations.
    cp = model.get_control_points()
    mom = np.zeros((dataset.number_of_subjects, cp.shape[0], cp.shape[1]))
    estimator.individual_RER['momenta'] = mom

    """
    Prior on the noise variance (inverse Wishart: scale scalars parameters).
    """

    td = Variable(torch.from_numpy(model.get_template_data()), requires_grad=False)
    cp = Variable(torch.from_numpy(cp), requires_grad=False)
    mom = Variable(torch.from_numpy(mom), requires_grad=False)
    residuals = model._compute_residuals(dataset, td, cp, mom).data.numpy()
    for k, object in enumerate(xml_parameters.template_specifications.values()):
        if object['noise_variance_prior_scale_std'] is None:
            model.priors['noise_variance'].scale_scalars.append(
                0.05 * residuals[k] / model.priors['noise_variance'].degrees_of_freedom[k])
        else:
            model.priors['noise_variance'].scale_scalars.append(object['noise_variance_prior_scale_std'] ** 2)
    model.update()


    """
    Launch.
    """

    if not os.path.exists(Settings().output_dir): os.makedirs(Settings().output_dir)

    model.name = 'BayesianAtlas'

    start_time = time.time()
    estimator.update()
    end_time = time.time()
    print('>> Estimation took: ' + str(time.strftime("%H:%M:%S", time.gmtime(end_time - start_time))))