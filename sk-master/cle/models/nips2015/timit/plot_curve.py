import ipdb
import numpy as np
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt

from cle.cle.utils import unpickle

#dir_path = '/raid/chungjun/repos/sk/cle/models/nips2015/timit/'
dir_path = '/data/lisatmp/chungjun/nips2015/timit/'
#models = ['m0_1', 'm1_1', 'm1_2',  'm2_1_re', 'm2_2', 'm3_1', 'm3_2']
models = ['m0_2', 'm1_2',  'm2_2', 'm3_2']
#labels = ['RNN-Gaussian', 'RNN-GMM', 'RNN-GMM0.1', 'RNN-VAEGauss', 'RNN-VAEGauss0.1', 'RNN-VAEGMM', 'RNN-VAEGMM0.1']
labels = ['RNN-Gaussian', 'RNN-GMM', 'RNN-VAEGauss', 'RNN-VAEGMM']
#colors = ['r', 'g', 'b', 'c', 'm', 'y', 'k']
colors = ['r', 'g', 'b', 'c']
save_name = 'valid_curves_1.png'

fig = plt.figure()
for i, model in enumerate(models):
    #exp = unpickle(dir_path + 'pkl/' + model + '_best.pkl')
    exp = unpickle(dir_path + 'pkl/' + model + '.pkl')
    mon = np.asarray(exp.trainlog._ddmonitors)

    #nll_lower_bound = mon[:, 0]
    nll_lower_bound = mon[1:, 0]
    legend_size = 10

    plt.plot(nll_lower_bound, color=colors[i], label=labels[i])
plt.legend(loc='upper right', prop={'size': legend_size})
plt.grid()
plt.savefig(dir_path + save_name, bbox_inches='tight', format='png')
