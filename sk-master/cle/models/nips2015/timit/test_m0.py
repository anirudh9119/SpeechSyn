import ipdb
import numpy as np
import theano
import theano.tensor as T

from cle.cle.cost import Gaussian
from cle.cle.data import Iterator
from cle.cle.utils import unpickle, tolist, OrderedDict
from cle.cle.utils.op import logsumexp

from sk.datasets.timit import TIMIT


#data_path = '/raid/chungjun/data/timit/readable/'
#exp_path = '/raid/chungjun/repos/sk/cle/models/nips2015/timit/pkl/'
#data_path = '/home/junyoung/data/timit/readable/'
#exp_path = '/home/junyoung/repos/sk/cle/models/nips2015/timit/pkl/'
data_path = '/data/lisa/data/timit/readable/'
exp_path = '/data/lisatmp/chungjun/nips2015/timit/pkl/'

frame_size = 200
# How many examples you want to proceed at a time
batch_size = 80
debug = 0

exp_name = 'm0_2_best'

train_data = TIMIT(name='train',
                   path=data_path,
                   frame_size=frame_size,
                   shuffle=0,
                   use_n_gram=1)

X_mean = train_data.X_mean
X_std = train_data.X_std

valid_data = TIMIT(name='valid',
                   path=data_path,
                   frame_size=frame_size,
                   shuffle=0,
                   use_n_gram=1,
                   X_mean=X_mean,
                   X_std=X_std)

x, x_mask = train_data.theano_vars()
if debug:
    x.tag.test_value = np.zeros((15, batch_size, frame_size), dtype=np.float32)
    temp = np.ones((15, batch_size), dtype=np.float32)
    temp[:, -2:] = 0.
    x_mask.tag.test_value = temp

exp = unpickle(exp_path + exp_name + '.pkl')
nodes = exp.model.nodes
ipdb.set_trace()
names = [node.name for node in nodes]

[main_lstm,
 x_1, x_2, x_3, x_4,
 theta_1, theta_2, theta_3, theta_4, theta_mu, theta_sig] = nodes


def inner_fn(x_t, s_tm1):

    x_1_t = x_1.fprop([x_t])
    x_2_t = x_2.fprop([x_1_t])
    x_3_t = x_3.fprop([x_2_t])
    x_4_t = x_4.fprop([x_3_t])

    theta_1_t = theta_1.fprop([s_tm1])
    theta_2_t = theta_2.fprop([theta_1_t])
    theta_3_t = theta_3.fprop([theta_2_t])
    theta_4_t = theta_4.fprop([theta_3_t])
    theta_mu_t = theta_mu.fprop([theta_4_t])
    theta_sig_t = theta_sig.fprop([theta_4_t])

    s_t = main_lstm.fprop([[x_4_t], [s_tm1]])

    return s_t, theta_mu_t, theta_sig_t

((s_t, theta_mu_t, theta_sig_t), updates) =\
    theano.scan(fn=inner_fn,
                sequences=[x],
                outputs_info=[main_lstm.get_init_state(batch_size),
                              None, None])

for k, v in updates.iteritems():
    k.default_update = v

reshaped_x = x.reshape((x.shape[0]*x.shape[1], -1))
reshaped_theta_mu = theta_mu_t.reshape((theta_mu_t.shape[0]*theta_mu_t.shape[1], -1))
reshaped_theta_sig = theta_sig_t.reshape((theta_sig_t.shape[0]*theta_sig_t.shape[1], -1))

recon = Gaussian(reshaped_x, reshaped_theta_mu, reshaped_theta_sig)
recon = recon.reshape((theta_mu_t.shape[0], theta_mu_t.shape[1]))
recon = recon * x_mask
recon_term = recon.sum(axis=0).mean()
recon_term.name = 'nll'

outputs = [recon_term]
monitor_fn = theano.function(inputs=[x, x_mask],
                             outputs=outputs,
                             on_unused_input='ignore',
                             allow_input_downcast=True)

DataProvider = [Iterator(valid_data, batch_size)]

data_record = []
for data in DataProvider:
    batch_record = []
    for batch in data:
        this_out = monitor_fn(*batch)
        batch_record.append(this_out)
    data_record.append(np.asarray(batch_record))
for record, data in zip(data_record, DataProvider):
    for i, ch in enumerate(outputs):
        this_mean = record[:, i].mean()
        if this_mean is np.nan:
            raise ValueError("NaN occured in output.")
        print("%s_%s: %f" % (data.name, ch.name, this_mean))
