import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + os.path.sep + '../../../')

from pydeformetrica.src.launch.estimate_deterministic_atlas import estimate_deterministic_atlas
from pydeformetrica.src.launch.estimate_bayesian_atlas import estimate_bayesian_atlas
from pydeformetrica.src.launch.estimate_geodesic_regression import estimate_geodesic_regression
from pydeformetrica.src.launch.run_shooting import run_shooting
from pydeformetrica.src.launch.compute_parallel_transport import compute_parallel_transport
from pydeformetrica.src.support.utilities.general_settings import Settings
from pydeformetrica.src.in_out.xml_parameters import XmlParameters

"""
Basic info printing.

"""

print('')
print('##############################')
print('##### PyDeformetrica 1.0 #####')
print('##############################')
print('')

"""
Read command line, read xml files, set general settings, and call the adapted function.
"""

assert len(sys.argv) >= 3, "Usage: " + sys.argv[0] + " <model.xml> <data_set.xml> <optimization_parameters.xml> " \
                                                     "<optionnal --output-dir=path_to_output"


model_xml_path = sys.argv[1]
dataset_xml_path = sys.argv[2]
optimization_parameters_xml_path = sys.argv[3]
if len(sys.argv) > 4:
    output_dir = sys.argv[4][len("--output-dir="):]
    print("Setting output directory to:", output_dir)
    Settings().set_output_dir(output_dir)

xml_parameters = XmlParameters()
xml_parameters.read_all_xmls(model_xml_path, dataset_xml_path, optimization_parameters_xml_path)


if xml_parameters.model_type == 'DeterministicAtlas'.lower():
    estimate_deterministic_atlas(xml_parameters)

elif xml_parameters.model_type == 'BayesianAtlas'.lower():
    estimate_bayesian_atlas(xml_parameters)

elif xml_parameters.model_type == 'Regression'.lower():
    estimate_geodesic_regression(xml_parameters)

elif xml_parameters.model_type == 'Shooting'.lower():
    run_shooting(xml_parameters)

elif xml_parameters.model_type == 'ParallelTransport'.lower():
    compute_parallel_transport(xml_parameters)

else:
    raise RuntimeError('Unrecognized model-type: "' + xml_parameters.model_type
                       + '". Check the corresponding field in the model.xml input file.')