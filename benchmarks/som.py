#setup: import numpy as np ; D = 2000; I = 1000; X = 20; Y = 20; G = [[np.random.rand(D) * 100.0 for i in range(Y)] for j in range(X)]; DATA = [np.random.rand(D) * 100.0 for i in range(D)]; tmp = np.empty(D)
#run: som(D,I,X,Y,G,DATA,tmp)

import numpy as np
import random

def bmu(grid, x, y, sel, tmp):
    """ calc the best matching unit, the one that has the smallest euclidean dist """
    min_dist, min_x, min_y = 0xffffffff, 0, 0
    for x in xrange(x):
        for y in xrange(y):
            entry = grid[x][y]
            np.subtract(sel, entry, out=tmp)
            # euclidean dist
            np.multiply(tmp, tmp, out=tmp)
            d = np.sqrt(tmp.sum())
            if d < min_dist:
                min_dist = d
                min_x = x
                min_y = y
    return min_x, min_y, min_dist

def som(D,I,X,Y,G,DATA,tmp):
    for j in xrange(I):
        i = random.randint(0,D-1)
        selection = DATA[i]
        x,y,dist = bmu(G, X, Y, selection, tmp)
        alpha = float(j)/I
        hci = 1 # do not bother, this func is not calc for this benchmark
        m = G[x][y]
        # m = m + alpha * hci * (m - sel)
        np.subtract(m, selection, out=tmp)
        np.multiply(tmp, alpha, out=tmp)
        np.multiply(tmp, hci, out=tmp)
        np.add(m, tmp, out=m)

        G[x][y] = m

    return None
