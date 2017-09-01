"""
    This file is part of hspace.

    hspace is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    gempy is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with hspace.  If not, see <http://www.gnu.org/licenses/>.
"""

import numpy as np
import matplotlib.pyplot as plt
import joblib # for parallel execution

# TODO at end: upload to pip, create setup.py (and conda install?) See also Tools -> Create setup.py!

# TODO: include both: a conventional calculation on the basis of probability fields,
# (as these may also be of interest), and the fast implementation based on sorting, for efficiency only


def joint_entropy(data_array, pos=None, **kwds):
    """Joint entropy between multiple points

    The data_array contains the multi-dimensional input data set. By default, the first axies
    should contain the realisations, and subsequent axes the dimensions within each realisation.

    Args:
        data_array (numpy.array): n-D array with input data
        pos (numpy.array): positions of points (n-1 -D) (in 1-D case: not required!)

    Attributes:
        extent(list):  [x_min, x_max, y_min, y_max, z_min, z_max]
        resolution ((Optional[list])): [nx, ny, nz]
        Foliations(pandas.core.frame.DataFrame): Pandas data frame with the foliations data
        Interfaces(pandas.core.frame.DataFrame): Pandas data frame with the interfaces data
        series(pandas.core.frame.DataFrame): Pandas data frame which contains every formation within each series

    """
    # TODO: implement in a way that it works on 1-D to 3-D data sets!


    # TODO: include check: first axis: relaisations; subsequent axes: dimensions within each
    # realisation

    # check possible implementation: if array is 1-D, then revert to bincount/ np.unique method
    # for faster implementation!


    # step 1: sort

    if len(data_array.shape) == 1: # 0-D case, no position argument required

        im_sort = np.sort(data_array) # , axis=0)

    # step 2: find change points/ switch points:
        switches = np.where(np.not_equal(im_sort[1:], im_sort[:-1]))[0]

    elif len(data_array.shape) == 2: # 1-D case, requires iteration over positions
        # im_sort = np.sort(data_array[:,pos], axis=0)
        # im_sort = data_array[np.argsort(data_array[:,0])]
        # new test as sorting did not return correct results:

        sub_array = np.empty((data_array.shape[0], len(pos)))
        i = 0
        for p1 in pos:
            sub_array[:, i] = data_array[:, p1]
            i += 1

        # now: sort:
        for i in range(len(pos)):
            sub_array = sub_array[sub_array[:, i].argsort(kind='mergesort')]

        switches = np.where(np.not_equal(sub_array[1:], sub_array[:-1]).any(axis=1))[0]

        # for p in pos:
        #     # data_array = data_array[data_array[:, p].argsort(kind='mergesort')]
        #     data_array = data_array[data_array[:, p].argsort(kind='mergesort')]
        #
        # # extract elements
        # # data_array = data_array[:,p]
        # switches = np.where(np.not_equal(data_array[1:], data_array[:-1]).any(axis=1))[0]
        # print(switches)

    elif len(data_array.shape) == 3: # 2-D case, requires iteration over positions
        # extract values:
        sub_array = np.empty((data_array.shape[0],len(pos)))
        i = 0
        for p1, p2 in pos:
            sub_array[:,i] = data_array[:,p1,p2]
            i += 1

        # now: sort:
        for i in range(len(pos)):
            sub_array = sub_array[sub_array[:, i].argsort(kind='mergesort')]

        switches = np.where(np.not_equal(sub_array[1:], sub_array[:-1]).any(axis=1))[0]
        #
        # for p1,p2 in pos:
        #     data_array = data_array[data_array[:, p1, p2].argsort(kind='mergesort')]
        #     # data_array = data_array[data_array[:, p].argsort(kind='mergesort')]
        # switches = np.where(np.not_equal(data_array[1:], data_array[:-1]).any(axis=1))[0]


    # determine differnces between switchpoints:
    n = data_array.shape[0]
    diff_array = np.diff(np.hstack([-1, switches, n - 1]))
    # print(tmp_switchpoints)
    # print(diff_switch)
    # print(np.sum(diff_switch))
    # determine probabilities:
    p = diff_array / n
    # calculate entropy
    H = np.sum(-p * np.log2(p))
    return H


class EntropySection(object):
    """Analyse (multivariate joint) entropy in 2-D section"""

    def __init__(self, data, pos=[], axis=0, n_jobs=1, *kwds):
        """Analyse (multivariate joint) entropy in 2-D section

        Default: entropy value at each location separately; when positions are given as argument,
        then the joint entropy between each position in the section and the position list is calculated.

        Parallel implemmentation using the python `joblib` package; the entropy itself is caculated with the
        sorting algorithm (see hspace.measures.joint_entropy())

        Args:
            data: Input data set for multiple realisations in one section (therefore: 3D)
            pos = list or array [[x1, x2, ...xn], [y1, y2, ...yn]]: list (or array)
                of fixed positions for multivariate joint entropy calculation
            axis: axis along which entropy is calculated (default: 0)
            n_jobs = int: number of processors to use for parallel execution (default: 1)
            **kwds:

        Returns:
            h : 2-D numpy array with calculated (joint) entropy values
        """
        self.data = data
        self.n_jobs = n_jobs
        self.axis = axis
        self.pos = pos

    def _calulate_entropy(self, **kwds):
        """Perform entropy calculation, in parallel if n_procs > 1

            **Optional keywords**:
            - n_jobs = int: number of processors to use for parallel execution (default: 1)

        """
        self.n_jobs = kwds.get('n_jobs', self.n_jobs)
        self.h = np.empty_like(self.data[0, :, :], dtype='float64')
        if self.n_jobs == 1:
            # standard sequential calculation:
            for i in range(self.data.shape[1]):
                for j in range(self.data.shape[2]):
                    self.h[i, j] = joint_entropy(self.data[:, i, j])

        else:
            global data # not ideal to create global variable - but required for parallel execution
            data = self.data
            h_par = joblib.Parallel(n_jobs=self.n_jobs)(joblib.delayed(entropy_section_par)(i, j)
                                       for i in range(self.data.shape[1])
                                       for j in range(self.data.shape[2]))

            h_par = np.array(h_par)
            self.h = h_par.reshape((self.data.shape[1], self.data.shape[2]))


    def _entropy_section_par(self, i, j):
        """Pure convencience fucntion for parallel execution!"""
        return joint_entropy(self.data[:, i, j])

    def plot_entropy(self, **kwds):
        """Create a plot of entropy

        If entropy has not been calculated (i.e. self.h does not exist), then this is automatically
        done here!

        Args:
            **kwds:
            n_jobs = int: number of processors to use for parallel execution (default: 1)

        Returns:

        """

        if not hasattr(self, "h"):
            self._calulate_entropy()

        plt.imshow(self.h.transpose(), origin='lower left')


    def plot_multiple(self, **kwds):
        """Plot multiple random section realisations in one plot

        This method can be useful to obtain a quick impression about the variability
        in the model output sections given the applied parameter distributions.
        Note that, by default, axis ticks and labels are removed for better visibility

        **Optional Keywords**:
            - *ncols* = int : number of columns (default: 8)
            - *nrows* = int : number of rows (default: 2)
            - *cmap* = matplotlib.cmap : colormap (default: YlOrRd)
            - *shuffle_events* = list of event ids : in addition to performing random draws, also
                randomly shuffle events in list
        """
        ncols = kwds.get("ncols", 6)
        nrows = kwds.get("nrows", 2)
        cmap_type = kwds.get('cmap', 'YlOrRd')
        ve = kwds.get("ve", 1.)
        savefig = kwds.get("savefig", False)
        figsize = kwds.get("figsize", (16, 5))

        k = 0  # index for image

        f, ax = plt.subplots(nrows, ncols, figsize=figsize)
        for j in range(ncols):
            for i in range(nrows):
                im = ax[i, j].imshow(self.data[k].T, interpolation='nearest',
                                     aspect=ve, cmap=cmap_type, origin='lower left')
                # remove ticks and labels
                ax[i, j].set_xticks([])
                ax[i, j].set_yticks([])
                # ax[i,j].imshow(im_subs_digit[j*nx+i])
                k += 1

        if savefig:
            fig_filename = kwds.get("fig_filename", "%s_random_sections_%s_pos_%d" % (self.basename, direction, cell_pos))
            plt.savefig(fig_filename, bbox_inches="tight")
        else:
            plt.show()


def entropy_section_par(i, j):
    return joint_entropy(data[:, i, j])


# %%timeit
def calc_parallel(data):


    h_par = joblib.Parallel(n_jobs=4)(joblib.delayed(entropy_section_par)(i,j) \
                          for i in range(data.shape[1])\
                          for j in range(data.shape[2]))
    h_par = np.array(h_par)
    h_par = h_par.reshape((data.shape[1],data.shape[2]))
    return h_par