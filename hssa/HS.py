# -*- coding: utf-8 -*-
import matplotlib.pyplot as plt
import scipy.io
import numpy as np
from scipy import ndimage
import weles
import operator

"""
A class to store and to use hypersectral image.
"""
class HS:
    """
    ## Initialization
    """
    def __init__(self, dictionary):
        # Loading image, ground truth and establishing informations.
        self.image = self.loadMatFromTuple(dictionary['image'])
        self.gt = self.loadMatFromTuple(dictionary['gt'])
        self.name = dictionary['name']
        self.classes = dictionary['classes']

        #print type(self.image[(0,0)][0])

        # Getting in shape.
        shape = np.shape(self.image)
        self.rows = shape[0]
        self.cols = shape[1]
        self.bands = shape[2]

        # Normalize
        self.normA = []
        self.normB = []
        for sliceIdx in xrange(self.bands):
            slice = self.slice(sliceIdx)
            #print sliceIdx
            minimum = np.min(slice)
            maximum = np.max(slice)
            self.normA.append(minimum)
            self.normB.append(maximum)
            #print slice
            #print 'min %i max %i' % (minimum, maximum)
        self.normB = map(operator.sub, self.normB, self.normA)
        #print self.normA
        #print self.normB


        # Searching for maximum value
        self.max = np.amax(self.image)
        self.maxlabel = np.amax(self.gt)

        self.reverseClasses = None
        self.prepareReverse()

    ## Operators

    def signatures(self):
        labels = set()
        result = {}
        # Establish list of labels, according to GT
        for row in self.gt:
            for item in row:
                if item not in labels:
                    labels.add(item)
        # Calculate mean signature for every label
        for label in labels:
            signatures = []
            for x, row in enumerate(self.gt):
                for y, item in enumerate(row):
                    if item == label:
                        signatures.append(self.signature((x, y)))
            result[label] = np.mean(signatures, axis = 0)
        # return the result
        return result

    def signaturesPNG(self, filename):
        signatures = self.signatures()

        # use LaTeX
        #plt.rc('text', usetex=True)
        #plt.rc('font', family='serif')
        #rcParams['font.sans-serif'] = ['Tahoma']

        # Plot size
        plt.figure(figsize=(11, 5.5))

        # Remove the plot frame lines. They are unnecessary chartjunk.
        ax = plt.subplot(111)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_visible(False)

        # Limit the range of the plot to only where the data is.
        # Avoid unnecessary whitespace.
        plt.ylim(0, 1)
        plt.xlim(0, self.bands)

        # Make sure your axis ticks are large enough to be easily read.
        # You don't want your viewers squinting to read your plot.
        plt.yticks(np.arange(0, 1, .1), [str(x) + "%" for x in range(0, 91, 10)], fontsize=14)
        plt.xticks(fontsize=14)

        # Provide tick lines across the plot to help your viewers trace along
        # the axis ticks. Make sure that the lines are light and small so they
        # don't obscure the primary data lines.
        for y in np.arange(.1, .91, .1):
            plt.plot(range(self.bands), [y] * len(range(self.bands)), "--", lw=0.5, color="black", alpha=0.3)

        # Remove the tick marks; they are unnecessary with the tick lines we just plotted.
        plt.tick_params(axis="both", which="both", bottom="on", top="off",
                        labelbottom="on", left="off", right="off", labelleft="on")

        # Actually plot signatures
        for item in signatures:
            line, = plt.plot(
                xrange(self.bands),
                signatures[item],
                linewidth = 1 )
            line.set_antialiased(True)

        plt.xlabel('Band')
        plt.ylabel('Normalized reflectance')

        plt.savefig(filename, bbox_inches='tight')

    """
    ### Getting sample
    """
    def sample(self, location):
        return weles.Sample(
            self.signature(location),
            self.label(location))

    """
    ### Getting signature
    """
    def signature(self, location):
        return (self.image[location].astype(float) - self.normA) / self.normB

    """
    ### Getting label
    """
    def label(self, location):
        return int(np.copy(self.gt[location]))

    """
    ### Getting slice
    """
    def slice(self, band):
        return np.copy(self.image[:, :, band])

    ## Helper functions

    def dynamicsTensor(self, slice, ksize):
        layers = ksize[0] * ksize[1]
        tensor = np.zeros((self.rows, self.cols, layers))
        i = 0
        for x in xrange(ksize[0]):
            for y in xrange(ksize[1]):
                kernel = np.zeros(ksize)
                kernel[x,y] = 1.

                smoothed = ndimage.convolve(slice, kernel, mode='reflect', cval=0.0)
                tensor[:,:,i] = smoothed
                i += 1

        return tensor


    def edges(self, ksize = (3, 3)):
        edges3d = np.zeros(np.shape(self.image))
        for sid in xrange(self.bands):
            slice = self.slice(sid)

            tensor = self.dynamicsTensor(slice, ksize)

            edges2d = np.subtract(
                np.amax(tensor, axis=2),
                np.amin(tensor, axis=2)
            )

            edges3d[:,:,sid] = edges2d

        return edges3d

    """
    ## Loading from .mat file
    """
    def loadMatFromTuple(self, entry):
        return scipy.io.loadmat(entry[0])[entry[1]]

    def prepareReverse(self):
        self.reverseClasses = {}
        for (x,y), value in np.ndenumerate(self.gt):
            label = self.label((x, y))
            if not label in self.reverseClasses:
                self.reverseClasses.update({label: len(self.reverseClasses)})

    """
    ## Exporting Weles dataset
    """
    def dataset(self):
        dataset = weles.Dataset()
        db_name = self.name
        source_samples = []
        self.reverseClasses = {}
        for x in xrange(self.rows):
            for y in xrange(self.cols):
                sample = self.sample((x, y))
                source_samples.append(sample)
                if not sample.label in self.reverseClasses:
                    self.reverseClasses.update({sample.label: len(self.reverseClasses)})
                sample.label = self.reverseClasses[sample.label]
        dataset.fill(
            db_name,
            source_samples,
            self.reverseClasses
        )
        print '# Classes\n%s' % self.reverseClasses
        return dataset


    """
    ## Be verbose, man
    """
    def __str__(self):
        return '%s image, %i classes, %i samples of %i bands' % (
            self.name,
            len(self.classes),
            self.rows * self.cols,
            self.bands)
