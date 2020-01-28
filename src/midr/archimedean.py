#!/usr/bin/python3

"""Compute the Irreproducible Discovery Rate (IDR) from NarrowPeaks files

Implementation of the IDR methods for two or more replicates.

LI, Qunhua, BROWN, James B., HUANG, Haiyan, et al. Measuring reproducibility
of high-throughput experiments. The annals of applied statistics, 2011,
vol. 5, no 3, p. 1752-1779.

Given a list of peak calls in NarrowPeaks format and the corresponding peak
call for the merged replicate. This tool computes and appends a IDR column to
NarrowPeaks files.
"""

import numpy as np
from scipy.optimize import minimize
from scipy.special import factorial
from scipy.special import binom
from scipy.stats import poisson
from mpmath import polylog


def lsum(x):
    """
    compute log sum_i x_i
    :param x:
    :return:
    """
    lx = np.log(x)
    x_max = max(lx)
    return x_max + np.log(np.sum(np.exp(lx - x_max), axis=0))


def lssum(x_values):
    """
    compute log sum_i x_i with sign
    :param x_values:
    :return:
    """
    b_i = np.sort(np.log(abs(x_values)))
    b_max = max(b_i)
    results = 0.0
    for i in range(x_values.shape[0]):
        if b_i[i] >= 0.0:
            results += np.exp(b_i[i] - b_max)
        else:
            results -= np.exp(b_i[i] - b_max)
    return b_max + np.log(results)


def log1mexp(x):
    """
    compute log(1-exp(-a)
    :param x:
    :return:
    """
    def mapping_function(x_val):
        """
        helper function to vectorize
        :param x_val:
        :return:
        """
        if x_val <= np.log(2.0):
            return np.log(-np.expm1(-x_val))
        else:
            return np.log1p(-np.exp(-x_val))
    mapping_function = np.vectorize(mapping_function)
    return mapping_function(x)


def log1pexp(x):
    """
    compute log(1 + exp(x))
    :param x:
    :return:
    """
    return np.logaddexp(0.0, x)


def diag_copula(u_values):
    """
    compute theta for a gumbel copula with DMLE
    :param u_values:
    :return: diagonal copula
    >>> diag_copula(np.array([
    ...    [0.72122885, 0.64249391, 0.6771109 ],
    ...    [0.48840676, 0.36490127, 0.27721709],
    ...    [0.63469281, 0.4517949 , 0.62365817],
    ...    [0.87942847, 0.15136347, 0.91851515],
    ...    [0.34839029, 0.05604025, 0.08416331],
    ...    [0.48967318, 0.99356872, 0.66912132],
    ...    [0.60683747, 0.4841944 , 0.22833209],
    ...    [0.30158193, 0.26186022, 0.05502786],
    ...    [0.51942063, 0.73040326, 0.25935125],
    ...    [0.46365886, 0.2459    , 0.83277053]
    ...    ]))
    array([0.72122885, 0.48840676, 0.63469281, 0.91851515, 0.34839029,
           0.99356872, 0.60683747, 0.30158193, 0.73040326, 0.83277053])
    """
    y = np.empty_like(u_values[:, 0])
    for i in range(u_values.shape[0]):
        y[i] = max(u_values[i, :])
    return y


def max_diag_pdf(u_values, diag_pdf, init, constraint):
    """
    find theta using dmle from diagonal pdf
    :param u_values:
    :param diag_pdf:
    :param init:
    :param constraint:
    :return:
    """
    def log_ddelta(theta, u_val):
        """
        helper function to compute the sum of the log pdf diag
        :param theta:
        :param u_val:
        :return:
        """
        return -np.sum(diag_pdf(u_values=u_val, theta=theta, is_log=True))

    res = minimize(
        fun=lambda x: log_ddelta(x, u_values),
        x0=np.array(init),
        constraints=constraint
    )
    if res.success:
        return res.x[0]
    else:
        return np.NaN


def dmle_copula_clayton(u_values):
    """
    compute clayton theta with DMLE
    :param u_values:
    :return:
    >>> dmle_copula_clayton( np.array([
    ...    [0.72122885, 0.64249391, 0.6771109 ],
    ...    [0.48840676, 0.36490127, 0.27721709],
    ...    [0.63469281, 0.4517949 , 0.62365817],
    ...    [0.87942847, 0.15136347, 0.91851515],
    ...    [0.34839029, 0.05604025, 0.08416331],
    ...    [0.48967318, 0.99356872, 0.66912132],
    ...    [0.60683747, 0.4841944 , 0.22833209],
    ...    [0.30158193, 0.26186022, 0.05502786],
    ...    [0.51942063, 0.73040326, 0.25935125],
    ...    [0.46365886, 0.2459    , 0.83277053]
    ...    ])
    ... )
    0.2740635891728625
    """
    return max_diag_pdf(
        u_values=u_values,
        diag_pdf=diag_pdf_clayton,
        init=0.5,
        constraint=[{'type': 'ineq', 'fun': lambda x: 1e-14},
                    {'type': 'ineq', 'fun': lambda x: 1000 - x}]
    )


def dmle_copula_franck(u_values):
    """
    compute franck theta with DMLE
    :param u_values:
    :return:
    >>> dmle_copula_franck(np.array([
    ...    [0.72122885, 0.64249391, 0.6771109 ],
    ...    [0.48840676, 0.36490127, 0.27721709],
    ...    [0.63469281, 0.4517949 , 0.62365817],
    ...    [0.87942847, 0.15136347, 0.91851515],
    ...    [0.34839029, 0.05604025, 0.08416331],
    ...    [0.48967318, 0.99356872, 0.66912132],
    ...    [0.60683747, 0.4841944 , 0.22833209],
    ...    [0.30158193, 0.26186022, 0.05502786],
    ...    [0.51942063, 0.73040326, 0.25935125],
    ...    [0.46365886, 0.2459    , 0.83277053]
    ...    ])
    ... )
    3.073701656631533
    """
    return max_diag_pdf(
        u_values=u_values,
        diag_pdf=diag_pdf_frank,
        init=0.5,
        constraint=[{'type': 'ineq', 'fun': lambda x: x - 1e-14},
                    {'type': 'ineq', 'fun': lambda x: 745 - x}]
    )


def ipsi_clayton(x, theta, is_log=False):
    """
    compute Clayton iPsi function
    :param x:
    :param theta:
    :param is_log:
    :return:
    >>> ipsi_clayton(np.array([
    ...    [0.42873569, 0.18285458, 0.9514195],
    ...    [0.25148149, 0.05617784, 0.3378213],
    ...    [0.79410993, 0.76175687, 0.0709562],
    ...    [0.02694249, 0.45788802, 0.6299574],
    ...    [0.39522060, 0.02189511, 0.6332237],
    ...    [0.66878367, 0.38075101, 0.5185625],
    ...    [0.90365653, 0.19654621, 0.6809525],
    ...    [0.28607729, 0.82713755, 0.7686878],
    ...    [0.22437343, 0.16907646, 0.5740400],
    ...    [0.66752741, 0.69487362, 0.3329266]
    ...    ]),
    ...    0.2,
    ...    is_log=True)
    array([[-1.68970664, -0.9046472 , -4.60419006],
           [-1.14586247, -0.25021206, -1.41715244],
           [-3.05365563, -2.88358502, -0.36029677],
           [ 0.05847131, -1.77732101, -2.33483902],
           [-1.58955921,  0.13757446, -2.34661855],
           [-2.47950927, -1.54631906, -1.96358583],
           [-3.88890049, -0.95569455, -2.52719433],
           [-1.25734211, -3.25226671, -2.91834924],
           [-1.05452015, -0.85128374, -2.14210478],
           [-2.47465594, -2.58334647, -1.40228078]])
    """
    if is_log:
        return np.log(np.sign(theta) * (x ** (-theta) - 1.0))
    return np.sign(theta) * (x ** (-theta) - 1.0)


def psi_clayton(x, theta):
    """
    compute Clayton Psi function
    :param x:
    :param theta:
    :return:
    >>> psi_clayton(np.array([
    ...    [0.42873569, 0.18285458, 0.9514195],
    ...    [0.25148149, 0.05617784, 0.3378213],
    ...    [0.79410993, 0.76175687, 0.0709562],
    ...    [0.02694249, 0.45788802, 0.6299574],
    ...    [0.39522060, 0.02189511, 0.6332237],
    ...    [0.66878367, 0.38075101, 0.5185625],
    ...    [0.90365653, 0.19654621, 0.6809525],
    ...    [0.28607729, 0.82713755, 0.7686878],
    ...    [0.22437343, 0.16907646, 0.5740400],
    ...    [0.66752741, 0.69487362, 0.3329266]
    ...    ]),
    ...    0.2)
    array([[0.16797341, 0.43186024, 0.03533839],
           [0.32574507, 0.7608775 , 0.23335089],
           [0.05379659, 0.058921  , 0.70980892],
           [0.87552668, 0.15183754, 0.0869198 ],
           [0.18914097, 0.89736349, 0.08605411],
           [0.07726802, 0.19926139, 0.12383307],
           [0.03999973, 0.40771118, 0.07451141],
           [0.28422656, 0.04910704, 0.05777555],
           [0.36343815, 0.45791558, 0.10349543],
           [0.07755952, 0.07150121, 0.23766697]])
    """
    return np.maximum(1.0 + np.sign(theta) * x, 0.0) ** (-1.0 / theta)


def pdf_clayton(u_values, theta, is_log=False):
    """
    compute clayton copula pdf
    :param u_values:
    :param theta:
    :param is_log:
    :return:
    >>> pdf_clayton(np.array([
    ...    [0.42873569, 0.18285458, 0.9514195],
    ...    [0.25148149, 0.05617784, 0.3378213],
    ...    [0.79410993, 0.76175687, 0.0709562],
    ...    [0.02694249, 0.45788802, 0.6299574],
    ...    [0.39522060, 0.02189511, 0.6332237],
    ...    [0.66878367, 0.38075101, 0.5185625],
    ...    [0.90365653, 0.19654621, 0.6809525],
    ...    [0.28607729, 0.82713755, 0.7686878],
    ...    [0.22437343, 0.16907646, 0.5740400],
    ...    [0.66752741, 0.69487362, 0.3329266]
    ...    ]),
    ...    0.2,
    ...    is_log=True)
    array([-0.12264018,  0.13487358, -0.40809375, -0.4061165 , -0.39266393,
            0.04690954, -0.10905049,  0.00406707,  0.00732412,  0.03587759])
    >>> pdf_clayton(np.array([
    ...    [0.42873569, 0.18285458, 0.9514195],
    ...    [0.25148149, 0.05617784, 0.3378213],
    ...    [0.79410993, 0.76175687, 0.0709562],
    ...    [0.02694249, 0.45788802, 0.6299574],
    ...    [0.39522060, 0.02189511, 0.6332237],
    ...    [0.66878367, 0.38075101, 0.5185625],
    ...    [0.90365653, 0.19654621, 0.6809525],
    ...    [0.28607729, 0.82713755, 0.7686878],
    ...    [0.22437343, 0.16907646, 0.5740400],
    ...    [0.66752741, 0.69487362, 0.3329266]
    ...    ]),
    ...    0.2)
    array([0.88458189, 1.1443921 , 0.66491654, 0.66623254, 0.67525564,
           1.0480272 , 0.89668514, 1.00407535, 1.007351  , 1.03652896])
    """
    dcopula = np.empty_like(u_values[:, 0])
    sum_seq = 0.0
    d = float(u_values.shape[1])
    t = np.sum(ipsi_clayton(x=u_values, theta=theta), axis=1)
    lu = np.sum(np.log(u_values), axis=1)
    const_a = np.log1p(theta)
    const_b = 1.0 + theta
    const_c = np.log1p(-t)
    if theta > 0.0:
        sum_seq = np.array([i for i in np.arange(1.0, d)])
        sum_seq = np.sum(np.log1p(theta * sum_seq))
        const_c = np.log1p(t)
    const_d = d + 1.0 / theta
    for i in range(u_values.shape[0]):
        if theta < 0.0:
            if t[i] < 1.0:
                dcopula[i] = const_a - const_b * lu[i] - const_d * const_c[i]
            else:
                dcopula[i] = -np.Inf
        elif theta > 0.0:
            dcopula[i] = sum_seq - const_b * lu[i] - const_d * const_c[i]
        else:
            dcopula[i] = 0.0
        if not is_log:
            dcopula[i] = np.exp(dcopula[i])
    return dcopula


def diag_pdf_clayton(u_values, theta, is_log=False):
    """
    compute clayton copula diagonal pdf
    :param u_values:
    :param theta:
    :param is_log:
    :return:
    >>> diag_pdf_clayton(np.array([
    ...    [0.42873569, 0.18285458, 0.9514195],
    ...    [0.25148149, 0.05617784, 0.3378213],
    ...    [0.79410993, 0.76175687, 0.0709562],
    ...    [0.02694249, 0.45788802, 0.6299574],
    ...    [0.39522060, 0.02189511, 0.6332237],
    ...    [0.66878367, 0.38075101, 0.5185625],
    ...    [0.90365653, 0.19654621, 0.6809525],
    ...    [0.28607729, 0.82713755, 0.7686878],
    ...    [0.22437343, 0.16907646, 0.5740400],
    ...    [0.66752741, 0.69487362, 0.3329266]
    ...    ]),
    ...    0.2,
    ...    is_log=True)
    array([ 0.98084835, -0.87814578,  0.58088657,  0.12305888,  0.13268952,
            0.23601368,  0.86262679,  0.66752968, -0.04581703,  0.31014911])
    >>> diag_pdf_clayton(np.array([
    ...    [0.42873569, 0.18285458, 0.9514195],
    ...    [0.25148149, 0.05617784, 0.3378213],
    ...    [0.79410993, 0.76175687, 0.0709562],
    ...    [0.02694249, 0.45788802, 0.6299574],
    ...    [0.39522060, 0.02189511, 0.6332237],
    ...    [0.66878367, 0.38075101, 0.5185625],
    ...    [0.90365653, 0.19654621, 0.6809525],
    ...    [0.28607729, 0.82713755, 0.7686878],
    ...    [0.22437343, 0.16907646, 0.5740400],
    ...    [0.66752741, 0.69487362, 0.3329266]
    ...    ]),
    ...    0.2)
    array([2.66671759, 0.41555273, 1.78762258, 1.13095101, 1.14189541,
           1.26619164, 2.36937639, 1.94941569, 0.95521672, 1.36362842])
    """
    y = diag_copula(u_values)
    d = float(u_values.shape[1])
    if is_log:
        return np.log(d) - (1.0 + 1.0 / theta) * np.log1p((d - 1.0) *
                                                          (1.0 - y ** theta))
    return d * (1.0 + (d - 1.0) * (1.0 - y ** theta)) ** (- (1.0 + 1.0 /
                                                             theta))


def dmle_copula_gumbel(u_values):
    """
    compute theta for a gumbel copula with DMLE
    :param u_values:
    :return: theta
    >>> dmle_copula_gumbel(np.array([
    ...    [0.72122885, 0.64249391, 0.6771109 ],
    ...    [0.48840676, 0.36490127, 0.27721709],
    ...    [0.63469281, 0.4517949 , 0.62365817],
    ...    [0.87942847, 0.15136347, 0.91851515],
    ...    [0.34839029, 0.05604025, 0.08416331],
    ...    [0.48967318, 0.99356872, 0.66912132],
    ...    [0.60683747, 0.4841944 , 0.22833209],
    ...    [0.30158193, 0.26186022, 0.05502786],
    ...    [0.51942063, 0.73040326, 0.25935125],
    ...    [0.46365886, 0.2459    , 0.83277053]
    ...    ]))
    1.5136102146750419
    """
    theta = np.log(float(u_values.shape[0])) - lsum(
        -np.log(diag_copula(u_values))
    )
    theta = np.log(float(u_values.shape[1])) / theta
    return max([theta, 1.0])


def ipsi_frank(u_values, theta, is_log=False):
    """
    Compute iPsi function for Frank copula
    :param u_values:
    :param theta:
    :param is_log:
    :return:
    >>> ipsi_frank(np.array([
    ...   [0.42873569, 0.18285458, 0.9514195],
    ...   [0.25148149, 0.05617784, 0.3378213],
    ...   [0.79410993, 0.76175687, 0.0709562],
    ...   [0.02694249, 0.45788802, 0.6299574],
    ...   [0.39522060, 0.02189511, 0.6332237],
    ...   [0.66878367, 0.38075101, 0.5185625],
    ...   [0.90365653, 0.19654621, 0.6809525],
    ...   [0.28607729, 0.82713755, 0.7686878],
    ...   [0.22437343, 0.16907646, 0.5740400],
    ...   [0.66752741, 0.69487362, 0.3329266]
    ...   ]),
    ...   0.2)
    array([[0.791148  , 1.61895993, 0.04510005],
           [1.30709475, 2.78651154, 1.02049626],
           [0.21055968, 0.24900271, 2.55444583],
           [3.51840984, 0.72823612, 0.42610361],
           [0.86923904, 3.72534678, 0.42125181],
           [0.37009377, 0.90510924, 0.60976894],
           [0.09197708, 1.54811406, 0.35325138],
           [1.1816307 , 0.17302414, 0.24062066],
           [1.41846307, 1.69593035, 0.51357717],
           [0.37185113, 0.33437415, 1.03460728]])
    """
    def mapping_function(x):
        """
        helper function for vectorize
        :param x:
        :return:
        """
        if x <= 0.01 * np.abs(theta):
            return - np.log(np.expm1(-x * theta) / np.expm1(-theta))
        else:
            if np.exp(-theta) > 0 and np.abs(theta - x * theta) < 1.0 / 2.0:
                return -np.log1p(np.exp(-theta) * np.expm1(theta - x * theta) /
                                 np.expm1(-theta))
            else:
                return -np.log1p((np.exp(-x * theta) - np.exp(-theta)) /
                                 np.expm1(-theta))
    mapping_function = np.vectorize(mapping_function)
    if is_log:
        return np.log(mapping_function(u_values))
    return mapping_function(u_values)


def psi_frank(u_values, theta):
    """
    Compute Psi function for Frank copula
    :param u_values:
    :param theta:
    :return:
    >>> psi_frank(np.array([
    ...   [0.42873569, 0.18285458, 0.9514195],
    ...   [0.25148149, 0.05617784, 0.3378213],
    ...   [0.79410993, 0.76175687, 0.0709562],
    ...   [0.02694249, 0.45788802, 0.6299574],
    ...   [0.39522060, 0.02189511, 0.6332237],
    ...   [0.66878367, 0.38075101, 0.5185625],
    ...   [0.90365653, 0.19654621, 0.6809525],
    ...   [0.28607729, 0.82713755, 0.7686878],
    ...   [0.22437343, 0.16907646, 0.5740400],
    ...   [0.66752741, 0.69487362, 0.3329266]
    ...   ]),
    ...   0.2)
    array([[0.62819295, 0.81834625, 0.36287933],
           [0.75972015, 0.93988774, 0.69230893],
           [0.42741191, 0.44210586, 0.92474177],
           [0.97065876, 0.60899809, 0.50765389],
           [0.65105904, 0.97608253, 0.50591179],
           [0.48734711, 0.66120387, 0.57101593],
           [0.38132619, 0.80627025, 0.4811596 ],
           [0.73189809, 0.41293628, 0.4389142 ],
           [0.78231684, 0.83069672, 0.53847762],
           [0.48799062, 0.47418202, 0.69595363]])
    >>> psi_frank(np.array([
    ...   [0.42873569, 0.18285458, 0.9514195],
    ...   [0.25148149, 0.05617784, 0.3378213],
    ...   [0.79410993, 0.76175687, 0.0709562],
    ...   [0.02694249, 0.45788802, 0.6299574],
    ...   [0.39522060, 0.02189511, 0.6332237],
    ...   [0.66878367, 0.38075101, 0.5185625],
    ...   [0.90365653, 0.19654621, 0.6809525],
    ...   [0.28607729, 0.82713755, 0.7686878],
    ...   [0.22437343, 0.16907646, 0.5740400],
    ...   [0.66752741, 0.69487362, 0.3329266]
    ...   ]),
    ...   -40)
    array([[0.98928161, 0.99542864, 0.97621451],
           [0.99371296, 0.99859555, 0.99155447],
           [0.98014725, 0.98095608, 0.9982261 ],
           [0.99932644, 0.9885528 , 0.98425106],
           [0.99011948, 0.99945262, 0.98416941],
           [0.98328041, 0.99048122, 0.98703594],
           [0.97740859, 0.99508634, 0.98297619],
           [0.99284807, 0.97932156, 0.9807828 ],
           [0.99439066, 0.99577309, 0.985649  ],
           [0.98331181, 0.98262816, 0.99167684]])
    >>> psi_frank(np.array([
    ...   [0.42873569, 0.18285458, 0.9514195],
    ...   [0.25148149, 0.05617784, 0.3378213],
    ...   [0.79410993, 0.76175687, 0.0709562],
    ...   [0.02694249, 0.45788802, 0.6299574],
    ...   [0.39522060, 0.02189511, 0.6332237],
    ...   [0.66878367, 0.38075101, 0.5185625],
    ...   [0.90365653, 0.19654621, 0.6809525],
    ...   [0.28607729, 0.82713755, 0.7686878],
    ...   [0.22437343, 0.16907646, 0.5740400],
    ...   [0.66752741, 0.69487362, 0.3329266]
    ...   ]),
    ...   -10)
    array([[0.95712886, 0.98171545, 0.90486527],
           [0.97485315, 0.99438248, 0.96621969],
           [0.92059451, 0.9238295 , 0.99290471],
           [0.99730587, 0.95421383, 0.93700824],
           [0.96048014, 0.99781059, 0.93668164],
           [0.93312595, 0.961927  , 0.94814684],
           [0.90964101, 0.98034637, 0.93190918],
           [0.97139377, 0.91729209, 0.92313647],
           [0.9775638 , 0.98309319, 0.94259952],
           [0.93325157, 0.93051719, 0.96670913]])
    """
    if theta > 0.0:
        return -log1mexp(u_values - log1mexp(theta)) / theta
    elif theta == 0.0:
        return np.exp(-u_values)
    elif theta < np.log(np.finfo(float).eps):
        return -log1pexp(-(u_values + theta)) / theta
    return - np.log1p(np.exp(-u_values) * np.expm1(-theta)) / theta


def diag_pdf_frank(u_values, theta, is_log=False):
    """
    compute frank copula diagonal pdf
    :param u_values:
    :param theta:
    :param is_log:
    :return:
    >>> diag_pdf_frank(np.array([
    ...    [0.42873569, 0.18285458, 0.9514195],
    ...    [0.25148149, 0.05617784, 0.3378213],
    ...    [0.79410993, 0.76175687, 0.0709562],
    ...    [0.02694249, 0.45788802, 0.6299574],
    ...    [0.39522060, 0.02189511, 0.6332237],
    ...    [0.66878367, 0.38075101, 0.5185625],
    ...    [0.90365653, 0.19654621, 0.6809525],
    ...    [0.28607729, 0.82713755, 0.7686878],
    ...    [0.22437343, 0.16907646, 0.5740400],
    ...    [0.66752741, 0.69487362, 0.3329266]
    ...    ]),
    ...    0.2,
    ...    is_log=True)
    array([ 0.9904959 , -1.00142163,  0.6200179 ,  0.17221735,  0.18204756,
            0.28624782,  0.88191526,  0.70127801, -0.00374368,  0.35967931])
    >>> diag_pdf_frank(np.array([
    ...    [0.42873569, 0.18285458, 0.9514195],
    ...    [0.25148149, 0.05617784, 0.3378213],
    ...    [0.79410993, 0.76175687, 0.0709562],
    ...    [0.02694249, 0.45788802, 0.6299574],
    ...    [0.39522060, 0.02189511, 0.6332237],
    ...    [0.66878367, 0.38075101, 0.5185625],
    ...    [0.90365653, 0.19654621, 0.6809525],
    ...    [0.28607729, 0.82713755, 0.7686878],
    ...    [0.22437343, 0.16907646, 0.5740400],
    ...    [0.66752741, 0.69487362, 0.3329266]
    ...    ]),
    ...    0.2)
    array([2.6925694 , 0.36735682, 1.85896133, 1.187936  , 1.19967124,
           1.33142237, 2.41552162, 2.01632796, 0.99626332, 1.43286983])
    """
    yt = diag_copula(u_values) * theta
    d = float(u_values.shape[1])

    def delt_dcom(x):
        """

        :param x:
        :return:
        """
        ep = ((np.exp(-x) - np.exp(x - theta)) / (-np.expm1(-x)))
        delt = np.exp(-x) * (1.0 + ep)
        d1 = d - 1.0
        dcom = d + d1 * ep
        dcom_time = (1.0 + ep) * delt
        return delt, dcom, dcom_time, d1

    def ddiagepoly2(x):
        """

        :param x:
        :return:
        """
        delt, dcom, dcom_time, d1 = delt_dcom(x)
        res = d1 * (d - 2.0) / 2.0 * (1.0 + (d - 3.0) / 3.0 *
                                      delt)
        res *= dcom_time
        res += dcom
        if is_log:
            return np.log(d) - np.log(res)
        return d / res

    def ddiagepoly4(x):
        """

        :param x:
        :return:
        """
        delt, dcom, dcom_time, d1 = delt_dcom(x)
        res = (d - 1.0) * (d - 2.0) / 2.0 * (1.0 + (d - 3.0) / 3.0 *
                                             delt *
                                             (1 + (d - 4.0) / 4.0 * delt * (
                                                     1.0 + (d - 5.0) / 5 * delt
                                             )))
        res *= dcom_time
        res += dcom
        if is_log:
            return np.log(d) - np.log(res)
        return d / res

    def ddiagem1(x):
        """

        :param x:
        :return:
        """
        h = -np.expm1(-theta)
        ie = -np.expm1(-x)
        res = (h / ie) ** (d - 1.0) - ie
        if is_log:
            return np.log(d) - x - np.log(res)
        return d * np.exp(-x) / res

    def mapping_function(x):
        """
        helper function to vectorize
        :param x:
        :return:
        """
        if x > 25:
            return ddiagepoly2(x)
        elif x < 0.1:
            return ddiagem1(x)
        else:
            return ddiagepoly4(x)

    mapping_function = np.vectorize(mapping_function)
    return mapping_function(yt)

def eulerian(n, m):
    dp = [[0 for x in range(m+1)]
             for y in range(n+1)]

    # For each row from 1 to n
    for i in range(1, n+1):

        # For each column from 0 to m
        for j in range(0, m+1):

            # If i is greater than j
            if (i > j):
                # If j is 0, then make that
                # state as 1.

                if (j == 0):
                    dp[i][j] = 1

                # basic recurrence relation.
                else :
                    dp[i][j] = (((i - j) *
                       dp[i - 1][j - 1]) +
                       ((j + 1) * dp[i - 1][j]))

    return dp[n][m]

def eulerian_all(n):
    """
    compute eulerian number
    :param n:
    :return:
    >>> eulerian_all(10)
    array([1.000000e+00, 1.013000e+03, 4.784000e+04, 4.551920e+05,
           1.310354e+06, 1.310354e+06, 4.551920e+05, 4.784000e+04,
           1.013000e+03, 1.000000e+00])
    """
    res = np.zeros(shape=n)
    for i in range(n):
        res[i] = eulerian(n, i)
    return res

def polyneval(coef, x):
    """

    :param coef:
    :param x:
    :return:
    >>> polyneval(eulerian_all(10), [-4, -3])
    array([1.12058925e+08, 9.69548800e+06])
    """
    vpolyval = np.vectorize(np.polyval, excluded=['p'])
    return vpolyval(p=coef, x=x)

def polylog(z, s, is_log_z=False):
    """

    :param z:
    :param s:
    :return:
    >>> polylog(np.array([0.01556112, 0.00108968, 0.00889932]), -2)
    array([-4.1004881 , -6.81751129, -4.68610299])
    """
    if is_log_z:
        w = z
        z = np.exp(w)
    n = -int(s)
    Eun = eulerian_all(n)
    p = polyneval(Eun, z)
    if is_log_z:
        return np.log(p) + w - (n + 1.0) * log1mexp(-w)
    else:
        return np.log(p) + np.log(z) - (n + 1.0) * np.log1p(-z)


def pdf_frank(u_values, theta, is_log=False):
    """
    compute frank copula pdf
    :param u_values:
    :param theta:
    :param is_log:
    :return:
    >>> pdf_frank(np.array([
    ...    [0.42873569, 0.18285458, 0.9514195],
    ...    [0.25148149, 0.05617784, 0.3378213],
    ...    [0.79410993, 0.76175687, 0.0709562],
    ...    [0.02694249, 0.45788802, 0.6299574],
    ...    [0.39522060, 0.02189511, 0.6332237],
    ...    [0.66878367, 0.38075101, 0.5185625],
    ...    [0.90365653, 0.19654621, 0.6809525],
    ...    [0.28607729, 0.82713755, 0.7686878],
    ...    [0.22437343, 0.16907646, 0.5740400],
    ...    [0.66752741, 0.69487362, 0.3329266]
    ...    ]),
    ...    0.2)
    array([0.94796045, 1.07458178, 0.91117583, 0.98067912, 0.99144689,
           0.9939432 , 0.94162409, 0.96927238, 1.02271257, 0.98591624])
    >>> pdf_frank(np.array([
    ...    [0.42873569, 0.18285458, 0.9514195],
    ...    [0.25148149, 0.05617784, 0.3378213],
    ...    [0.79410993, 0.76175687, 0.0709562],
    ...    [0.02694249, 0.45788802, 0.6299574],
    ...    [0.39522060, 0.02189511, 0.6332237],
    ...    [0.66878367, 0.38075101, 0.5185625],
    ...    [0.90365653, 0.19654621, 0.6809525],
    ...    [0.28607729, 0.82713755, 0.7686878],
    ...    [0.22437343, 0.16907646, 0.5740400],
    ...    [0.66752741, 0.69487362, 0.3329266]
    ...    ]),
    ...    0.2,
    ...    is_log=True)
    array([-0.05344249,  0.07193155, -0.09301939, -0.01950997, -0.00858989,
           -0.00607522, -0.06014914, -0.03120961,  0.02245848, -0.01418388])
    """
    if theta == 0.0:
        copula = np.zeros(shape=u_values.shape[0])
    else:
        d = float(u_values.shape[1])
        usum = np.sum(u_values, axis=1)
        lp = log1mexp(theta)
        lpu = log1mexp(theta * u_values)
        lu = np.sum(lpu, axis=1)
        liarg = -np.expm1(-theta) * np.exp(np.sum(lpu-lp, axis=1))
        li = polylog(
            liarg,
            -(d - 1.0)
        )
        copula = (d - 1.0) * np.log(theta) + li - theta * usum - lu
    if is_log:
        return copula
    return np.exp(copula)


def ipsi_gumbel(u_values, theta, is_log=False):
    """
    Compute iPsi function for gumbel copula
    :param u_values:
    :param theta:
    :param is_log:
    :return:
    >>> ipsi_gumbel(np.array([
    ...   [0.42873569, 0.18285458, 0.9514195],
    ...   [0.25148149, 0.05617784, 0.3378213],
    ...   [0.79410993, 0.76175687, 0.0709562],
    ...   [0.02694249, 0.45788802, 0.6299574],
    ...   [0.39522060, 0.02189511, 0.6332237],
    ...   [0.66878367, 0.38075101, 0.5185625],
    ...   [0.90365653, 0.19654621, 0.6809525],
    ...   [0.28607729, 0.82713755, 0.7686878],
    ...   [0.22437343, 0.16907646, 0.5740400],
    ...   [0.66752741, 0.69487362, 0.3329266]
    ...   ]),
    ...   1.2)
    array([[0.81923327, 1.88908593, 0.02733237],
           [1.47231458, 3.55739554, 1.10313864],
           [0.17190186, 0.20976237, 3.21401011],
           [4.67297101, 0.74347847, 0.3959922 ],
           [0.91460233, 4.99665702, 0.39068015],
           [0.33531508, 0.95887481, 0.60372092],
           [0.06408581, 1.79316182, 0.31736126],
           [1.30892336, 0.13611697, 0.20141246],
           [1.61947932, 1.99408403, 0.49340591],
           [0.33719654, 0.29741158, 1.1209654 ]])
    >>> ipsi_gumbel(np.array([
    ...   [0.42873569, 0.18285458, 0.9514195],
    ...   [0.25148149, 0.05617784, 0.3378213],
    ...   [0.79410993, 0.76175687, 0.0709562],
    ...   [0.02694249, 0.45788802, 0.6299574],
    ...   [0.39522060, 0.02189511, 0.6332237],
    ...   [0.66878367, 0.38075101, 0.5185625],
    ...   [0.90365653, 0.19654621, 0.6809525],
    ...   [0.28607729, 0.82713755, 0.7686878],
    ...   [0.22437343, 0.16907646, 0.5740400],
    ...   [0.66752741, 0.69487362, 0.3329266]
    ...   ]),
    ...   1.2, is_log=True)
    array([[-0.19938642,  0.63609307, -3.59968356],
           [ 0.38683571,  1.26902869,  0.09815943],
           [-1.76083155, -1.56177998,  1.16751941],
           [ 1.54179506, -0.29641547, -0.92636075],
           [-0.08926592,  1.60876909, -0.93986609],
           [-1.09268464, -0.04199476, -0.50464323],
           [-2.74753233,  0.58398044, -1.14771453],
           [ 0.26920494, -1.9942407 , -1.60240044],
           [ 0.48210469,  0.69018481, -0.70642309],
           [-1.08708931, -1.21263832,  0.11419028]])
    """
    if is_log:
        return theta * np.log(-np.log(u_values))
    return (-np.log(u_values)) ** theta


def psi_gumbel(u_values, theta):
    """
    Compute Psi function for Frank copula
    :param u_values:
    :param theta:
    :return:
    >>> psi_gumbel(np.array([
    ...   [0.42873569, 0.18285458, 0.9514195],
    ...   [0.25148149, 0.05617784, 0.3378213],
    ...   [0.79410993, 0.76175687, 0.0709562],
    ...   [0.02694249, 0.45788802, 0.6299574],
    ...   [0.39522060, 0.02189511, 0.6332237],
    ...   [0.66878367, 0.38075101, 0.5185625],
    ...   [0.90365653, 0.19654621, 0.6809525],
    ...   [0.28607729, 0.82713755, 0.7686878],
    ...   [0.22437343, 0.16907646, 0.5740400],
    ...   [0.66752741, 0.69487362, 0.3329266]
    ...   ]),
    ...   1.2)
    array([[0.61034427, 0.78449875, 0.38314216],
           [0.72866953, 0.91322228, 0.66711104],
           [0.43814072, 0.45063321, 0.89558443],
           [0.95198356, 0.59359729, 0.50641834],
           [0.63043035, 0.95944934, 0.50493238],
           [0.48911264, 0.63939466, 0.56071577],
           [0.39890033, 0.77277837, 0.48384529],
           [0.70297971, 0.42582847, 0.44791995],
           [0.74988568, 0.79662481, 0.53276337],
           [0.48966058, 0.47790784, 0.67038358]])
    """
    return np.exp(-u_values ** (1.0 / theta))


def diag_pdf_gumbel(u_values, theta, is_log=False):
    """
    compute frank copula diagonal pdf
    :param u_values:
    :param theta:
    :param is_log:
    :return:
    >>> diag_pdf_gumbel(np.array([
    ...    [0.42873569, 0.18285458, 0.9514195],
    ...    [0.25148149, 0.05617784, 0.3378213],
    ...    [0.79410993, 0.76175687, 0.0709562],
    ...    [0.02694249, 0.45788802, 0.6299574],
    ...    [0.39522060, 0.02189511, 0.6332237],
    ...    [0.66878367, 0.38075101, 0.5185625],
    ...    [0.90365653, 0.19654621, 0.6809525],
    ...    [0.28607729, 0.82713755, 0.7686878],
    ...    [0.22437343, 0.16907646, 0.5740400],
    ...    [0.66752741, 0.69487362, 0.3329266]
    ...    ]),
    ...    0.2,
    ...    is_log=True)
    array([  -6.55858673, -257.13458817,  -50.29601565, -106.33588414,
           -105.08436706,  -91.86224008,  -19.02297494,  -40.4347328 ,
           -128.83053864,  -82.60105914])
    >>> diag_pdf_gumbel(np.array([
    ...    [0.42873569, 0.18285458, 0.9514195],
    ...    [0.25148149, 0.05617784, 0.3378213],
    ...    [0.79410993, 0.76175687, 0.0709562],
    ...    [0.02694249, 0.45788802, 0.6299574],
    ...    [0.39522060, 0.02189511, 0.6332237],
    ...    [0.66878367, 0.38075101, 0.5185625],
    ...    [0.90365653, 0.19654621, 0.6809525],
    ...    [0.28607729, 0.82713755, 0.7686878],
    ...    [0.22437343, 0.16907646, 0.5740400],
    ...    [0.66752741, 0.69487362, 0.3329266]
    ...    ]),
    ...    0.2)
    array([1.41788815e-003, 2.12748865e-112, 1.43455743e-022, 6.59040780e-047,
           2.30377070e-046, 1.27272929e-040, 5.47553997e-009, 2.75054445e-018,
           1.12100608e-056, 1.33910865e-036])
    """
    y = diag_copula(u_values)
    d = float(u_values.shape[1])
    alpha = 1.0 / theta
    da = d ** alpha
    if is_log:
        return (da - 1.0) * np.log(y) + alpha * np.log(d)
    return da * y ** (da - 1.0)


def pdf_gumbel(u_values, theta, is_log=False):
    """
    compute frank copula pdf
    :param u_values:
    :param theta:
    :param is_log:
    :return:
    >>> pdf_gumbel(np.array([
    ...    [0.42873569, 0.18285458, 0.9514195],
    ...    [0.25148149, 0.05617784, 0.3378213],
    ...    [0.79410993, 0.76175687, 0.0709562],
    ...    [0.02694249, 0.45788802, 0.6299574],
    ...    [0.39522060, 0.02189511, 0.6332237],
    ...    [0.66878367, 0.38075101, 0.5185625],
    ...    [0.90365653, 0.19654621, 0.6809525],
    ...    [0.28607729, 0.82713755, 0.7686878],
    ...    [0.22437343, 0.16907646, 0.5740400],
    ...    [0.66752741, 0.69487362, 0.3329266]
    ...    ]),
    ...    1.2)
    array([0.62097606, 1.39603813, 0.58225969, 0.85072331, 0.88616848,
           1.10022557, 0.66461897, 0.33769735, 1.15561848, 1.01957628])
    >>> pdf_gumbel(np.array([
    ...    [0.42873569, 0.18285458, 0.9514195],
    ...    [0.25148149, 0.05617784, 0.3378213],
    ...    [0.79410993, 0.76175687, 0.0709562],
    ...    [0.02694249, 0.45788802, 0.6299574],
    ...    [0.39522060, 0.02189511, 0.6332237],
    ...    [0.66878367, 0.38075101, 0.5185625],
    ...    [0.90365653, 0.19654621, 0.6809525],
    ...    [0.28607729, 0.82713755, 0.7686878],
    ...    [0.22437343, 0.16907646, 0.5740400],
    ...    [0.66752741, 0.69487362, 0.3329266]
    ...    ]),
    ...    1.2,
    ...    is_log=True)
    array([-0.47646275,  0.33363832, -0.54083873, -0.16166834, -0.12084819,
            0.09551522, -0.40854139, -1.08560521,  0.14463568,  0.01938713])
    """

    def s_j(j, alpha_var, d_var):
        """
        sign function
        :param j:
        :param alpha_var:
        :param d_var:
        :return:
        """
        assert 0.0 < alpha_var
        assert alpha_var <= 1.0
        assert d_var >= 0.0 and 0.0 <= float(j)
        if alpha_var == 1.0:
            if int(j) == int(d_var):
                return 1.0
            else:
                return (-1.0)**(d_var - float(j))
        else:
            x = alpha_var * float(j)
            if x != np.floor(x):
                return (-1.0)**(float(j)-np.ceil(x))
            else:
                return 0.0

    def log_polyg(lx_var, alpha_var, d_var):
        """
        compute gumbel polylog
        :param lx_var:
        :param alpha_var:
        :param d_var:
        :return:
        """
        res = np.zeros(shape=int(d_var))
        x = np.exp(lx_var)
        for j in range(1, int(d_var) + 1):
            res[j-1] += np.log(abs(binom(alpha_var * float(j), d_var)))
            res[j-1] += np.log(factorial(d_var))
            res[j-1] += float(j) * lx_var
            res[j-1] += x - np.log(factorial(float(j)))
            res[j-1] += poisson.logcdf(d_var - float(j), x)
            res[j-1] = s_j(j, alpha_var, d_var) * np.exp(res[j - 1])
        return lssum(res)

    d = float(u_values.shape[1])
    alpha = 1.0 / theta
    lip = ipsi_gumbel(u_values, theta)
    lnt = np.zeros(shape=u_values.shape[0])
    for i in range(u_values.shape[0]):
        lnt[i] = lsum(lip[i, :])
    mlu = -np.log(u_values)
    lmlu = np.log(mlu)
    lx = alpha * lnt
    ls = np.zeros(shape=u_values.shape[0])
    for i in range(u_values.shape[0]):
        ls[i] = log_polyg(lx[i], alpha, d) - d * lx[i] / alpha
    lnc = -np.exp(lx)
    dcopula = lnc + d * np.log(theta) + np.sum((theta - 1.0) * lmlu + mlu,
                                               axis=1) + ls
    if is_log:
        return dcopula
    return np.exp(dcopula)
