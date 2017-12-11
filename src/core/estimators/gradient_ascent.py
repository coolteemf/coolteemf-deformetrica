import os.path
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + os.path.sep + '../../../')

from pydeformetrica.src.core.estimators.abstract_estimator import AbstractEstimator

import numpy as np
from decimal import Decimal
import torch
import math

class GradientAscent(AbstractEstimator):

    """
    GradientAscent object class.
    An estimator is an algorithm which updates the fixed effects of a statistical model.

    """

    ####################################################################################################################
    ### Constructor:
    ####################################################################################################################

    def __init__(self):
        AbstractEstimator.__init__(self)

        self.CurrentFixedEffects = None
        self.CurrentAttachement = None
        self.CurrentRegularity = None
        self.CurrentLogLikelihood = None

        self.InitialStepSize = None
        self.MaxLineSearchIterations = None

        self.LineSearchShrink = None
        self.LineSearchExpand = None
        self.ConvergenceTolerance = None


    ####################################################################################################################
    ### Public methods:
    ####################################################################################################################

    def Update(self):

        """
        Runs the gradient ascent algorithm and updates the statistical model.

        """

        # Initialisation -----------------------------------------------------------------------------------------------
        self.CurrentFixedEffects = {key: value.flatten()
                                    for key, value in self.StatisticalModel.GetFixedEffects().items()}

        self.CurrentAttachement, self.CurrentRegularity, fixedEffectsGrad = self.StatisticalModel.ComputeLogLikelihood(
            self.Dataset, self.CurrentFixedEffects, None, None, with_grad=True)
        self.CurrentLogLikelihood = self.CurrentAttachement + self.CurrentRegularity
        self.Print()

        initialLogLikelihood = self.CurrentLogLikelihood
        lastLogLikelihood = initialLogLikelihood

        nbParams = len(fixedEffectsGrad)
        step = np.ones((nbParams,)) * self.InitialStepSize

        # Main loop ----------------------------------------------------------------------------------------------------
        for iter in range(1, self.MaxIterations + 1):
            self.CurrentIteration = iter

            # Line search ----------------------------------------------------------------------------------------------
            foundMin = False
            for li in range(self.MaxLineSearchIterations):

                # Print step size --------------------------------------------------------------------------------------
                if not(iter % self.PrintEveryNIters):
                    k = 0
                    print('>> Step size = ')
                    for key in fixedEffectsGrad.keys():
                        print('\t ' + str(step[k]) + ' [' + key + ']')
                        k += 1

                # Try a simple gradient ascent step --------------------------------------------------------------------
                newFixedEffects = self.GradientAscentStep(self.CurrentFixedEffects, fixedEffectsGrad, step)
                newAttachement, newRegularity = self.StatisticalModel.ComputeLogLikelihood(
                    self.Dataset, newFixedEffects, None, None)

                Q = (newAttachement + newRegularity).data.numpy()[0] - lastLogLikelihood
                if Q > 0:
                    foundMin = True
                    break

                # Adapting the step sizes ------------------------------------------------------------------------------
                elif nbParams > 1:
                    step *= self.LineSearchShrink

                    newFixedEffects_prop = [None] * nbParams
                    newAttachement_prop = [None] * nbParams
                    newRegularity_prop = [None] * nbParams
                    Q_prop = [None] * nbParams

                    for k in range(nbParams):
                        localStep = step
                        localStep[k] /= self.LineSearchShrink

                        newFixedEffects_prop[k] = self.GradientAscentStep(
                            self.CurrentFixedEffects, fixedEffectsGrad, localStep)
                        newAttachement_prop[k], newRegularity_prop[k] = self.StatisticalModel.ComputeLogLikelihood(
                            self.Dataset, self.CurrentFixedEffects, None, None)

                        Q_prop[k] = (newAttachement_prop[k] + newRegularity_prop[k]).data.numpy()[0] - lastLogLikelihood

                    index = Q_prop.index(max(Q_prop))
                    if Q_prop[index] > 0:
                        newAttachement = newAttachement_prop[index]
                        newRegularity = newRegularity_prop[index]
                        newFixedEffects = newFixedEffects_prop[index]
                        step[index] /= self.LineSearchShrink
                        foundMin = True
                        break

                else:
                    step *= self.LineSearchShrink

            # End of line search ---------------------------------------------------------------------------------------
            if not(foundMin):
                self.StatisticalModel.SetFixedEffects(self.CurrentFixedEffects)
                print('>> Number of line search loops exceeded. Stopping.')
                break

            self.CurrentAttachement = newAttachement
            self.CurrentRegularity = newRegularity
            self.CurrentLogLikelihood = newAttachement + newRegularity
            self.CurrentFixedEffects = newFixedEffects

            # Test the stopping criterion ------------------------------------------------------------------------------
            currentLogLikelihood = self.CurrentLogLikelihood.data.numpy()[0]
            deltaF_current = lastLogLikelihood - currentLogLikelihood
            deltaF_initial = initialLogLikelihood - currentLogLikelihood

            if math.fabs(deltaF_current) < self.ConvergenceTolerance * math.fabs(deltaF_initial):
                print('>> Tolerance threshold met. Stopping the optimization process.\n')
                break

            # Printing and writing -------------------------------------------------------------------------------------
            if not(iter % self.PrintEveryNIters):
                self.Print()

            if not(iter % self.SaveEveryNIters):
                self.Write()

            # Prepare next iteration -----------------------------------------------------------------------------------
            step *= self.LineSearchExpand
            lastLogLikelihood = currentLogLikelihood

            self.CurrentLogLikelihood.backward()
            fixedEffectsGrad = {key: value.grad
                                for key, value in self.CurrentFixedEffects.items() if value.requires_grad}

        # Finalization -------------------------------------------------------------------------------------------------
        print('>> Write output files ...')
        self.Write()
        print('>> Done.')


    def Print(self):
        """
        Prints information.
        """
        print('')
        print('------------------------------------- Iteration: ' + str(self.CurrentIteration)
              + ' -------------------------------------')
        print('>> Log-likelihood = %.3E \t [ attachement = %.3E ; regularity = %.3E ]' %
              (Decimal(str(self.CurrentLogLikelihood.data.numpy()[0])),
               Decimal(str(self.CurrentAttachement.data.numpy()[0])),
               Decimal(str(self.CurrentRegularity.data.numpy()[0]))))

    def Write(self):
        """
        Save the current results.
        """
        self.StatisticalModel.SetFixedEffects(self.CurrentFixedEffects)
        self.StatisticalModel.Write(self.Dataset)


    ####################################################################################################################
    ### Private methods:
    ####################################################################################################################

    def GradientAscentStep(self, fixedEffects, fixedEffectsGrad, step):
        newFixedEffects = {key: value.clone() for key, value in fixedEffects.items()}

        for k, key in enumerate(fixedEffectsGrad.keys()):
            newFixedEffects[key] = fixedEffects[key] + fixedEffectsGrad[key] * step[k]

        return newFixedEffects