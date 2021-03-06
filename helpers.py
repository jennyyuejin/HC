import numpy as np
from scipy.stats import norm
import matplotlib.pyplot as plt


def plot_losses(timeVec, lossVec, bestTime = None, timeWindowLen=None, show=True, presetTitle=None, xlabel=None):
    """
    @param presetTitle: if None, use default; if '', no title
    @param xlabel: if None, use no xlabel
    """

    plt.margins(0.5)
    plt.plot(timeVec, lossVec, 'o')

    if xlabel is not None:
        plt.xlabel('Time')

    plt.ylabel('Loss')

    minX = 2*timeVec[0]-timeVec[1]
    minY = min(lossVec)*0.9
    plt.xlim(xmin=minX)  # padding
    plt.ylim(ymin=minY)

    if presetTitle is None:
        title = 'Losses on A Timeline'
    elif presetTitle == '':
        title = None
    else:
        title = presetTitle


    # time window
    if bestTime is not None:
        plt.axvspan(bestTime, bestTime + timeWindowLen - 1, facecolor='g', alpha=0.5)

        if presetTitle is None:
            title += ' (Time Window = ' + str(timeWindowLen) + ')'

    if title is not None:
        plt.title(title)

    if show:
        plt.show()


def simulate_times(expiration, numLosses, method, verbose=False):
    """
    simulate the loss timeline
    time distribution: equal intervals
    @param method: controls the distribution of time points. is one of:
        "even": evenly spread out
        "unif": uniform random
        "poisson": poisson distribution
    @returns: timeVec
    """

    assert method in ['even', 'unif', 'poisson']

    timeVec = None

    if method == 'even':
        interval = 1. * expiration / numLosses
        timeVec = np.arange(start=0, stop=expiration, step=interval).round()    # whole days only

    elif method == 'unif':
        timeVec = np.sort(np.random.randint(low=0, high=expiration, size=numLosses))

    elif method == 'poisson':
        temp = np.random.exponential(expiration/numLosses, numLosses).cumsum()  # simulate
        timeVec = (temp / max(temp) * expiration).round()    # scale and round

    assert len(timeVec) == numLosses

    if verbose:
        print timeVec

    return timeVec


def simulate_losses(numLosses, minLoss, maxLoss, method, sd=0, verbose=False):
    """
    simulate losses
    loss distribution: uniform random
    @param method: one of:
        "uniform": Unif[minLoss, maxLoss]
        "monoDec": monotonically decreasing from maxLoss to minLoss with white noise N(0, sd)
        "monoInc": monotonically increasing from minLoss to maxLoss with white noise N(0, sd)
        "bell" : bell shaped between minLoss and maxLoss with white noise N(0, sd)
    @param sd: standard deviation of the white noise term
    @returns: lossVec
    """

    assert method in ['uniform', 'monoDec', 'monoInc', 'bell']

    noises = np.random.normal(0, sd, size=numLosses) if sd>0 else [0]*numLosses

    if method == 'uniform':     # Unif[minLoss, maxLoss]
        means = np.random.uniform(low=minLoss, high=maxLoss, size=numLosses)

    elif method == 'monoDec':   # monotonically decreasing from maxLoss to minLoss with white noise N(0, sd)
        means = np.arange(start=maxLoss, stop=minLoss, step=-1.*(maxLoss-minLoss)/numLosses)

    elif method == 'monoInc':   # monotonically decreasing from maxLoss to minLoss with white noise N(0, sd)
        means = np.arange(start=minLoss, stop=maxLoss, step=1.*(maxLoss-minLoss)/numLosses)

    elif method == 'bell':  # bell shaped between minLoss and maxLoss with white noise N(0, sd)
        means = (maxLoss - minLoss) * norm.pdf(np.linspace(start=-3, stop=3, num=numLosses)) + minLoss

    lossVec = means + noises

    assert len(lossVec) == numLosses

    if verbose:
        print lossVec

    return lossVec


def treaty_CatXL(deductible, limit):
    """ generates the CatXL treaty function
    @returns: a function
    """

    assert limit > deductible, 'Limit cannot be less than deductible.'

    return lambda losses: min(max(sum(losses) - deductible, 0), limit - deductible)


def treaty_inuring_CatXL(d1, l1, d2, l2):
    """ generates a 2-level inuring CatXL treaty structure
    @returns: a function
    """

    assert l1 > d1 and l2 > d2, 'Limits cannot be less than deductibles.'

    def res_func(losses):
        payout1 = treaty_CatXL(d1, l1)(losses)
        leftover = sum(losses) - payout1
        payout2 = min(max(leftover - d2, 0), l2 - d2)

        return payout1 + payout2

    return res_func


def treaty_CatXL_program(dVec, lVec):
    """
    generates a program (i.e. non-overlapping CatXL treaties on a single inuring level)
    @returns: a function
    """

    for i, d in enumerate(dVec):
        assert d < lVec[i], 'Limits cannot be less than attachment points.'

        if i > 0:
            assert d >= lVec[i-1], 'No overlaps are allowed.'

    def res_func(losses):
        return sum(treaty_CatXL(d, lVec[i])(losses) for i, d in enumerate(dVec))

    return res_func


def find_window(windowLen, treatyFunc, timeVec, lossVec, verbose=2):
    """
    find the optimal window given losses on a timeline
    @param verbose: verbosity level, up to 3
    @returns: bestTime, maxPayout
    """

    maxPayout = 0
    bestTimes = []

    for i, t in enumerate(timeVec):
        curTimes = timeVec[i:] < t + windowLen
        curLosses = lossVec[i:][curTimes]
        payout = treatyFunc(curLosses)

        # printing
        if verbose >= 2:
            print '---- t =', t
            if verbose >= 3:
                print 'curTimes:', curTimes
                print 'curLosses:', curLosses
            print 'payout:', payout

        if payout == maxPayout:
            if verbose >= 1:
                print 'Duplicate max payout found. Adding time', t

            bestTimes.append(t)

        elif payout > maxPayout:

            if verbose >= 1:
                print 'Replacing old maxPayout', maxPayout, 'with new', payout, '; new best time is', t

            maxPayout = payout
            bestTimes = [t]

    return bestTimes[0], bestTimes, maxPayout
