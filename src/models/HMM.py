# -*- coding: utf-8 -*-

#
# HMM model implementation of HMM Aligner
# Simon Fraser University
# NLP Lab
#
# This is the implementation of HMM word aligner, it requires IBM1 in order to
# function properly
#
import numpy as np
from collections import defaultdict
from loggers import logging
from models.IBM1 import AlignmentModel as AlignerIBM1
from models.modelBase import Task
from models.HMMBase import AlignmentModelBase as Base
from evaluators.evaluator import evaluate
__version__ = "0.5a"


class AlignmentModel(Base):
    def __init__(self):
        self.modelName = "HMM"
        self.version = "0.2b"
        self.logger = logging.getLogger('HMM')
        self.p0H = 0.3
        self.nullEmissionProb = 0.000005
        self.smoothFactor = 0.1
        self.task = None
        self.evaluate = evaluate
        self.fLex = self.eLex = self.fIndex = self.eIndex = None

        self.modelComponents = ["t", "pi", "a", "eLengthSet",
                                "fLex", "eLex", "fIndex", "eIndex"]
        Base.__init__(self)
        return

    def _beginningOfIteration(self, dataset, maxE):
        self.lenDataset = len(dataset)
        self.gammaEWord = defaultdict(float)
        self.gammaBiword = defaultdict(float)
        self.gammaSum_0 = np.zeros(maxE)
        return

    def gamma(self, f, e, alpha, beta, alphaScale):
        return ((alpha * beta).T / alphaScale).T

    def _updateEndOfIteration(self, maxE, delta):
        self.logger.info("End of iteration")
        # Update a
        for Len in self.eLengthSet:
            for prev_j in range(Len):
                deltaSum = 0.0
                for j in range(Len):
                    deltaSum += delta[Len][prev_j][j]
                for j in range(Len):
                    self.a[Len][prev_j][j] = delta[Len][prev_j][j] /\
                        (deltaSum + 1e-37)

        # Update pi
        for i in range(maxE):
            self.pi[i] = self.gammaSum_0[i] * (1.0 / self.lenDataset)

        # Update t
        self.t = np.zeros(self.t.shape)
        for f, e in self.gammaBiword:
            self.t[f][e] = self.gammaBiword[(f, e)] / self.gammaEWord[e]
        return

    def endOfBaumWelch(self):
        # Smoothing for target sentences of unencountered length
        for targetLen in self.eLengthSet:
            a = self.a[targetLen]
            for prev_j in range(targetLen):
                for j in range(targetLen):
                    a[prev_j][j] *= 1 - self.p0H
        for targetLen in self.eLengthSet:
            a = self.a[targetLen]
            for prev_j in range(targetLen):
                for j in range(targetLen):
                    a[prev_j][prev_j + targetLen] = self.p0H
                    a[prev_j + targetLen][prev_j + targetLen] = self.p0H
                    a[prev_j + targetLen][j] = a[prev_j][j]
        return

    def train(self, dataset, iterations):
        dataset = self.initialiseLexikon(dataset)
        self.task = Task("Aligner", "HMMOI" + str(iterations))
        self.task.progress("Training IBM model 1")
        self.logger.info("Training IBM model 1")
        alignerIBM1 = AlignerIBM1()
        alignerIBM1.sharedLexikon(self)
        alignerIBM1.initialiseBiwordCount(dataset)
        alignerIBM1.EM(dataset, iterations, 'IBM1')
        self.t = alignerIBM1.t
        self.task.progress("IBM model Trained")
        self.logger.info("IBM model Trained")
        self.baumWelch(dataset, iterations=iterations)
        self.task.progress("finalising")
        self.task = None
        return
