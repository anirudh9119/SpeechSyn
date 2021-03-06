import ipdb
import numpy as np
import theano
import theano.tensor as T

from cle.cle.data import Iterator
from cle.cle.cost import GMM
from cle.cle.models import Model
from cle.cle.layers import InitCell
from cle.cle.layers.feedforward import FullyConnectedLayer
from cle.cle.layers.layer import PriorLayer
from cle.cle.layers.recurrent import LSTM
from cle.cle.train import Training
from cle.cle.train.ext import (
    EpochCount,
    GradientClipping,
    Monitoring,
    Picklize,
    EarlyStopping,
    WeightNorm
)
from cle.cle.train.opt import Adam
from cle.cle.utils import flatten, sharedX
from cle.cle.utils.compat import OrderedDict
from sk.datasets.blizzard_h5 import Blizzard_h5_tbptt


data_path = '/raid/chungjun/data/blizzard_unseg/'
save_path = '/raid/chungjun/repos/sk/cle/models/nips2015/blizzard/pkl/'

reset_freq = 4
batch_size = 128
mn_batch_size = 1280
frame_size = 200
latent_size = 200
lstm_1_dim = 1860
lstm_2_dim = 1860
lstm_3_dim = 1860
q_z_dim = 400
p_z_dim = 400
p_x_dim = 400
x2s_dim = 400
z2s_dim = 400
k = 20
target_size = frame_size * k
lr = 3e-4
debug = 0

file_name = 'blizzard_unseg_tbptt'
normal_params = np.load(data_path + file_name + '_normal.npz')
X_mean = normal_params['X_mean']
X_std = normal_params['X_std']

model = Model()
train_data = Blizzard_h5_tbptt(name='train',
                               path=data_path,
                               frame_size=frame_size,
                               file_name=file_name,
                               X_mean=X_mean,
                               X_std=X_std)

valid_data = Blizzard_h5_tbptt(name='valid',
                               path=data_path,
                               frame_size=frame_size,
                               file_name=file_name,
                               X_mean=X_mean,
                               X_std=X_std)

init_W = InitCell('rand')
init_U = InitCell('ortho')
init_b = InitCell('zeros')
#init_b_sig = InitCell('const', mean=0.6)
init_b_sig = InitCell('const')

x = train_data.theano_vars()
mn_x = valid_data.theano_vars()
if debug:
    x.tag.test_value = np.zeros((15, batch_size, frame_size), dtype=np.float32)
    mn_x.tag.test_value = np.zeros((15, mn_batch_size, frame_size), dtype=np.float32)

x_1 = FullyConnectedLayer(name='x_1',
                          parent=['x_t'],
                          parent_dim=[frame_size],
                          nout=x2s_dim,
                          unit='relu',
                          init_W=init_W,
                          init_b=init_b)

x_2 = FullyConnectedLayer(name='x_2',
                          parent=['x_1'],
                          parent_dim=[x2s_dim],
                          nout=x2s_dim,
                          unit='relu',
                          init_W=init_W,
                          init_b=init_b)

x_3 = FullyConnectedLayer(name='x_3',
                          parent=['x_2'],
                          parent_dim=[x2s_dim],
                          nout=x2s_dim,
                          unit='relu',
                          init_W=init_W,
                          init_b=init_b)

x_4 = FullyConnectedLayer(name='x_4',
                          parent=['x_3'],
                          parent_dim=[x2s_dim],
                          nout=x2s_dim,
                          unit='relu',
                          init_W=init_W,
                          init_b=init_b)

x_5 = FullyConnectedLayer(name='x_5',
                          parent=['x_4'],
                          parent_dim=[x2s_dim],
                          nout=x2s_dim,
                          unit='relu',
                          init_W=init_W,
                          init_b=init_b)

x_6 = FullyConnectedLayer(name='x_6',
                          parent=['x_5'],
                          parent_dim=[x2s_dim],
                          nout=x2s_dim,
                          unit='relu',
                          init_W=init_W,
                          init_b=init_b)

z_1 = FullyConnectedLayer(name='z_1',
                          parent=['z_t'],
                          parent_dim=[latent_size],
                          nout=z2s_dim,
                          unit='relu',
                          init_W=init_W,
                          init_b=init_b)

z_2 = FullyConnectedLayer(name='z_2',
                          parent=['z_1'],
                          parent_dim=[z2s_dim],
                          nout=z2s_dim,
                          unit='relu',
                          init_W=init_W,
                          init_b=init_b)

z_3 = FullyConnectedLayer(name='z_3',
                          parent=['z_2'],
                          parent_dim=[z2s_dim],
                          nout=z2s_dim,
                          unit='relu',
                          init_W=init_W,
                          init_b=init_b)

z_4 = FullyConnectedLayer(name='z_4',
                          parent=['z_3'],
                          parent_dim=[z2s_dim],
                          nout=z2s_dim,
                          unit='relu',
                          init_W=init_W,
                          init_b=init_b)

lstm_1 = LSTM(name='lstm_1',
              parent=['x_6', 'z_4'],
              parent_dim=[x2s_dim, z2s_dim],
              batch_size=batch_size,
              nout=lstm_1_dim,
              unit='tanh',
              init_W=init_W,
              init_U=init_U,
              init_b=init_b)

lstm_2 = LSTM(name='lstm_2',
              parent=['lstm_1'],
              parent_dim=[lstm_1_dim],
              batch_size=batch_size,
              nout=lstm_2_dim,
              unit='tanh',
              init_W=init_W,
              init_U=init_U,
              init_b=init_b)

lstm_3 = LSTM(name='lstm_3',
              parent=['lstm_2'],
              parent_dim=[lstm_2_dim],
              batch_size=batch_size,
              nout=lstm_3_dim,
              unit='tanh',
              init_W=init_W,
              init_U=init_U,
              init_b=init_b)

phi_1 = FullyConnectedLayer(name='phi_1',
                            parent=['x_6', 's_3_tm1'],
                            parent_dim=[x2s_dim, lstm_3_dim],
                            nout=q_z_dim,
                            unit='relu',
                            init_W=init_W,
                            init_b=init_b)

phi_2 = FullyConnectedLayer(name='phi_2',
                            parent=['phi_1'],
                            parent_dim=[q_z_dim],
                            nout=q_z_dim,
                            unit='relu',
                            init_W=init_W,
                            init_b=init_b)

phi_3 = FullyConnectedLayer(name='phi_3',
                            parent=['phi_2'],
                            parent_dim=[q_z_dim],
                            nout=q_z_dim,
                            unit='relu',
                            init_W=init_W,
                            init_b=init_b)

phi_4 = FullyConnectedLayer(name='phi_4',
                            parent=['phi_3'],
                            parent_dim=[q_z_dim],
                            nout=q_z_dim,
                            unit='relu',
                            init_W=init_W,
                            init_b=init_b)

phi_mu = FullyConnectedLayer(name='phi_mu',
                             parent=['phi_4'],
                             parent_dim=[q_z_dim],
                             nout=latent_size,
                             unit='linear',
                             init_W=init_W,
                             init_b=init_b)

phi_sig = FullyConnectedLayer(name='phi_sig',
                              parent=['phi_4'],
                              parent_dim=[q_z_dim],
                              nout=latent_size,
                              unit='softplus',
                              cons=1e-4,
                              init_W=init_W,
                              init_b=init_b_sig)

prior = PriorLayer(name='prior',
                   parent=['phi_mu', 'phi_sig'],
                   parent_dim=[latent_size, latent_size],
                   use_sample=1,
                   num_sample=1,
                   nout=latent_size)

prior_1 = FullyConnectedLayer(name='prior_1',
                              parent=['s_3_tm1'],
                              parent_dim=[lstm_3_dim],
                              nout=p_z_dim,
                              unit='relu',
                              init_W=init_W,
                              init_b=init_b)

prior_2 = FullyConnectedLayer(name='prior_2',
                              parent=['prior_1'],
                              parent_dim=[p_z_dim],
                              nout=p_z_dim,
                              unit='relu',
                              init_W=init_W,
                              init_b=init_b)

prior_3 = FullyConnectedLayer(name='prior_3',
                              parent=['prior_2'],
                              parent_dim=[p_z_dim],
                              nout=p_z_dim,
                              unit='relu',
                              init_W=init_W,
                              init_b=init_b)

prior_4 = FullyConnectedLayer(name='prior_4',
                              parent=['prior_3'],
                              parent_dim=[p_z_dim],
                              nout=p_z_dim,
                              unit='relu',
                              init_W=init_W,
                              init_b=init_b)

prior_mu = FullyConnectedLayer(name='prior_mu',
                               parent=['prior_4'],
                               parent_dim=[p_z_dim],
                               nout=latent_size,
                               unit='linear',
                               init_W=init_W,
                               init_b=init_b)

prior_sig = FullyConnectedLayer(name='prior_sig',
                                parent=['prior_4'],
                                parent_dim=[p_z_dim],
                                nout=latent_size,
                                unit='softplus',
                                cons=1e-4,
                                init_W=init_W,
                                init_b=init_b_sig)

kl = PriorLayer(name='kl',
                parent=['phi_mu', 'phi_sig', 'prior_mu', 'prior_sig'],
                parent_dim=[latent_size, latent_size, latent_size, latent_size],
                use_sample=0,
                nout=latent_size)

theta_1 = FullyConnectedLayer(name='theta_1',
                              parent=['z_4', 's_3_tm1'],
                              parent_dim=[z2s_dim, lstm_3_dim],
                              nout=p_x_dim,
                              unit='relu',
                              init_W=init_W,
                              init_b=init_b)

theta_2 = FullyConnectedLayer(name='theta_2',
                              parent=['theta_1'],
                              parent_dim=[p_x_dim],
                              nout=p_x_dim,
                              unit='relu',
                              init_W=init_W,
                              init_b=init_b)

theta_3 = FullyConnectedLayer(name='theta_3',
                              parent=['theta_2'],
                              parent_dim=[p_x_dim],
                              nout=p_x_dim,
                              unit='relu',
                              init_W=init_W,
                              init_b=init_b)

theta_4 = FullyConnectedLayer(name='theta_4',
                              parent=['theta_3'],
                              parent_dim=[p_x_dim],
                              nout=p_x_dim,
                              unit='relu',
                              init_W=init_W,
                              init_b=init_b)

theta_mu = FullyConnectedLayer(name='theta_mu',
                               parent=['theta_4'],
                               parent_dim=[p_x_dim],
                               nout=target_size,
                               unit='linear',
                               init_W=init_W,
                               init_b=init_b)

theta_sig = FullyConnectedLayer(name='theta_sig',
                                parent=['theta_4'],
                                parent_dim=[p_x_dim],
                                nout=target_size,
                                unit='softplus',
                                cons=1e-4,
                                init_W=init_W,
                                init_b=init_b_sig)

coeff = FullyConnectedLayer(name='coeff',
                            parent=['theta_4'],
                            parent_dim=[p_x_dim],
                            nout=k,
                            unit='softmax',
                            init_W=init_W,
                            init_b=init_b)

nodes = [lstm_1, lstm_2, lstm_3, prior, kl,
         x_1, x_2, x_3, x_4, x_5, x_6,
         z_1, z_2, z_3, z_4,
         phi_1, phi_2, phi_3, phi_4, phi_mu, phi_sig,
         prior_1, prior_2, prior_3, prior_4, prior_mu, prior_sig,
         theta_1, theta_2, theta_3, theta_4, theta_mu, theta_sig, coeff]

for node in nodes:
    node.initialize()

params = flatten([node.get_params().values() for node in nodes])

step_count = sharedX(0, name='step_count')
last_lstm_1 = np.zeros((batch_size, lstm_1_dim*2), dtype=theano.config.floatX)
last_lstm_2 = np.zeros((batch_size, lstm_2_dim*2), dtype=theano.config.floatX)
last_lstm_3 = np.zeros((batch_size, lstm_3_dim*2), dtype=theano.config.floatX)
lstm_1_tm1 = sharedX(last_lstm_1, name='lstm_1_tm1')
lstm_2_tm1 = sharedX(last_lstm_2, name='lstm_2_tm1')
lstm_3_tm1 = sharedX(last_lstm_3, name='lstm_3_tm1')
update_list = [step_count, lstm_1_tm1, lstm_2_tm1, lstm_3_tm1]

step_count = T.switch(T.le(step_count, reset_freq), step_count + 1, 0)
s_1_0 = T.switch(T.or_(T.cast(T.eq(step_count, 0), 'int32'),
                       T.cast(T.eq(T.sum(lstm_1_tm1), 0.), 'int32')),
                 lstm_1.get_init_state(batch_size), lstm_1_tm1)
s_2_0 = T.switch(T.or_(T.cast(T.eq(step_count, 0), 'int32'),
                       T.cast(T.eq(T.sum(lstm_2_tm1), 0.), 'int32')),
                 lstm_2.get_init_state(batch_size), lstm_2_tm1)
s_3_0 = T.switch(T.or_(T.cast(T.eq(step_count, 0), 'int32'),
                       T.cast(T.eq(T.sum(lstm_3_tm1), 0.), 'int32')),
                 lstm_3.get_init_state(batch_size), lstm_3_tm1)

x_shape = x.shape
x_in = x.reshape((x_shape[0]*x_shape[1], -1))
x_1_in = x_1.fprop([x_in])
x_2_in = x_2.fprop([x_1_in])
x_3_in = x_3.fprop([x_2_in])
x_4_in = x_4.fprop([x_3_in])
x_5_in = x_5.fprop([x_4_in])
x_6_in = x_6.fprop([x_5_in])
x_6_in = x_6_in.reshape((x_shape[0], x_shape[1], -1))


def inner_fn(x_t, s_tm1):

    phi_1_t = phi_1.fprop([x_t, s_3_tm1])
    phi_2_t = phi_2.fprop([phi_1_t])
    phi_3_t = phi_3.fprop([phi_2_t])
    phi_4_t = phi_4.fprop([phi_3_t])
    phi_mu_t = phi_mu.fprop([phi_4_t])
    phi_sig_t = phi_sig.fprop([phi_4_t])

    prior_1_t = prior_1.fprop([s_3_tm1])
    prior_2_t = prior_2.fprop([prior_1_t])
    prior_3_t = prior_3.fprop([prior_2_t])
    prior_4_t = prior_4.fprop([prior_3_t])
    prior_mu_t = prior_mu.fprop([prior_4_t])
    prior_sig_t = prior_sig.fprop([prior_4_t])

    z_t = prior.fprop([phi_mu_t, phi_sig_t])
    z_1_t = z_1.fprop([z_t])
    z_2_t = z_2.fprop([z_1_t])
    z_3_t = z_3.fprop([z_2_t])
    z_4_t = z_4.fprop([z_3_t])

    s_1_t = lstm_1.fprop([[x_t, z_4_t], [s_1_tm1]])
    s_2_t = lstm_2.fprop([[s_1_t], [s_2_tm1]])
    s_3_t = lstm_3.fprop([[s_2_t], [s_3_tm1]])

    return s_1_t, s_2_t, s_3_t, phi_mu_t, phi_sig_t, prior_mu_t, prior_sig_t, z_4_t

((s_1_t, s_2_t, s_3_t, phi_mu_t, phi_sig_t, prior_mu_t, prior_sig_t, z_4_t), updates) =\
    theano.scan(fn=inner_fn,
                sequences=[x_6_in],
                outputs_info=[s_1_0, s_2_0, s_3_0, None, None, None, None, None])

for k, v in updates.iteritems():
    k.default_update = v

lstm_1_tm1 = s_1_t[-1]
lstm_2_tm1 = s_2_t[-1]
s_3_t, lstm_3_tm1 = s_3_t[:-1], s_3_t[-1]
s_shape = s_3_t.shape
s_in = T.concatenate([s_3_0, s_3_t.reshape((s_shape[0]*s_shape[1], -1))], axis=0)
z_4_shape = z_4_t.shape
z_4_in = z_4_t.reshape((z_4_shape[0]*z_4_shape[1], -1))
theta_1_in = theta_1.fprop([z_4_in, s_in])
theta_2_in = theta_2.fprop([theta_1_in])
theta_3_in = theta_3.fprop([theta_2_in])
theta_4_in = theta_4.fprop([theta_3_in])
theta_mu_in = theta_mu.fprop([theta_4_in])
theta_sig_in = theta_sig.fprop([theta_4_in])
coeff_in = coeff.fprop([theta_4_in])

z_shape = phi_mu_t.shape
phi_mu_in = phi_mu_t.reshape((z_shape[0]*z_shape[1], -1))
phi_sig_in = phi_sig_t.reshape((z_shape[0]*z_shape[1], -1))
prior_mu_in = prior_mu_t.reshape((z_shape[0]*z_shape[1], -1))
prior_sig_in = prior_sig_t.reshape((z_shape[0]*z_shape[1], -1))
kl_in = kl.fprop([phi_mu_in, phi_sig_in, prior_mu_in, prior_sig_in])
kl_t = kl_in.reshape((z_shape[0], z_shape[1]))

recon = GMM(x_in, theta_mu_in, theta_sig_in, coeff_in)
recon = recon.reshape((x_shape[0], x_shape[1]))
recon_term = recon.mean()
kl_term = kl_t.mean()
nll_lower_bound = recon_term + kl_term
nll_lower_bound.name = 'nll_lower_bound'

mn_x_shape = mn_x.shape
mn_x_in = mn_x.reshape((mn_x_shape[0]*mn_x_shape[1], -1))
mn_x_1_in = x_1.fprop([mn_x_in])
mn_x_2_in = x_2.fprop([mn_x_1_in])
mn_x_3_in = x_3.fprop([mn_x_2_in])
mn_x_4_in = x_4.fprop([mn_x_3_in])
mn_x_5_in = x_5.fprop([mn_x_4_in])
mn_x_6_in = x_6.fprop([mn_x_5_in])
mn_x_6_in = mn_x_6_in.reshape((mn_x_shape[0], mn_x_shape[1], -1))
mn_s_1_0 = lstm_1.get_init_state(mn_batch_size)
mn_s_2_0 = lstm_2.get_init_state(mn_batch_size)
mn_s_3_0 = lstm_3.get_init_state(mn_batch_size)

((mn_s_1_t, mn_s_2_t, mn_s_3_t, mn_phi_mu_t, mn_phi_sig_t, mn_prior_mu_t, mn_prior_sig_t, mn_z_4_t), mn_updates) =\
    theano.scan(fn=inner_fn,
                sequences=[mn_x_6_in],
                outputs_info=[mn_s_1_0, mn_s_2_0, mn_s_3_0, None, None, None, None, None])

for k, v in mn_updates.iteritems():
    k.default_update = v

mn_s_3_t = mn_s_3_t[:-1]
mn_s_shape = mn_s_3_t.shape
mn_s_in = T.concatenate([mn_s_3_0, mn_s_3_t.reshape((mn_s_shape[0]*mn_s_shape[1], -1))], axis=0)
mn_z_4_shape = mn_z_4_t.shape
mn_z_4_in = mn_z_4_t.reshape((mn_z_4_shape[0]*mn_z_4_shape[1], -1))
mn_theta_1_in = theta_1.fprop([mn_z_4_in, mn_s_in])
mn_theta_2_in = theta_2.fprop([mn_theta_1_in])
mn_theta_3_in = theta_3.fprop([mn_theta_2_in])
mn_theta_4_in = theta_4.fprop([mn_theta_3_in])
mn_theta_mu_in = theta_mu.fprop([mn_theta_4_in])
mn_theta_sig_in = theta_sig.fprop([mn_theta_4_in])
mn_coeff_in = coeff.fprop([mn_theta_4_in])

mn_z_shape = mn_phi_mu_t.shape
mn_phi_mu_in = mn_phi_mu_t.reshape((mn_z_shape[0]*mn_z_shape[1], -1))
mn_phi_sig_in = mn_phi_sig_t.reshape((mn_z_shape[0]*mn_z_shape[1], -1))
mn_prior_mu_in = mn_prior_mu_t.reshape((mn_z_shape[0]*mn_z_shape[1], -1))
mn_prior_sig_in = mn_prior_sig_t.reshape((mn_z_shape[0]*mn_z_shape[1], -1))
mn_kl_in = kl.fprop([mn_phi_mu_in, mn_phi_sig_in, mn_prior_mu_in, mn_prior_sig_in])
mn_kl_t = mn_kl_in.reshape((mn_z_shape[0], mn_z_shape[1]))

mn_recon = GMM(mn_x_in, mn_theta_mu_in, mn_theta_sig_in, mn_coeff_in)
mn_recon = mn_recon.reshape((mn_x_shape[0], mn_x_shape[1]))
mn_recon_term = mn_recon.mean()
mn_kl_term = mn_kl_t.mean()
mn_nll_lower_bound = mn_recon_term + mn_kl_term
mn_nll_lower_bound.name = 'nll_lower_bound'
mn_recon_term.name = 'recon_term'
mn_kl_term.name = 'kl_term'

mn_kl_ratio = mn_kl_term / T.abs_(mn_recon_term)
mn_kl_ratio.name = 'kl_term proportion'

max_x = mn_x.max()
mean_x = mn_x.mean()
min_x = mn_x.min()
max_x.name = 'max_x'
mean_x.name = 'mean_x'
min_x.name = 'min_x'

max_theta_mu = mn_theta_mu_in.max()
mean_theta_mu = mn_theta_mu_in.mean()
min_theta_mu = mn_theta_mu_in.min()
max_theta_mu.name = 'max_theta_mu'
mean_theta_mu.name = 'mean_theta_mu'
min_theta_mu.name = 'min_theta_mu'

max_theta_sig = mn_theta_sig_in.max()
mean_theta_sig = mn_theta_sig_in.mean()
min_theta_sig = mn_theta_sig_in.min()
max_theta_sig.name = 'max_theta_sig'
mean_theta_sig.name = 'mean_theta_sig'
min_theta_sig.name = 'min_theta_sig'

max_phi_sig = mn_phi_sig_t.max()
mean_phi_sig = mn_phi_sig_t.mean()
min_phi_sig = mn_phi_sig_t.min()
max_phi_sig.name = 'max_phi_sig'
mean_phi_sig.name = 'mean_phi_sig'
min_phi_sig.name = 'min_phi_sig'

max_prior_sig = mn_prior_sig_t.max()
mean_prior_sig = mn_prior_sig_t.mean()
min_prior_sig = mn_prior_sig_t.min()
max_prior_sig.name = 'max_prior_sig'
mean_prior_sig.name = 'mean_prior_sig'
min_prior_sig.name = 'min_prior_sig'

model.inputs = [x]
model._params = params
model.nodes = nodes
model.set_updates(update_list)

optimizer = Adam(
    lr=lr
)

mn_fn = theano.function(inputs=[mn_x],
                        outputs=[mn_nll_lower_bound, mn_recon_term, mn_kl_term, mn_kl_ratio,
                                 max_phi_sig, mean_phi_sig, min_phi_sig,
                                 max_prior_sig, mean_prior_sig, min_prior_sig,
                                 max_theta_sig, mean_theta_sig, min_theta_sig,
                                 max_x, mean_x, min_x,
                                 max_theta_mu, mean_theta_mu, min_theta_mu],
                        on_unused_input='ignore')

extension = [
    GradientClipping(batch_size=batch_size),
    EpochCount(4),
    Monitoring(freq=1000,
               monitor_fn=mn_fn,
               ddout=[mn_nll_lower_bound, mn_recon_term, mn_kl_term, mn_kl_ratio,
                      max_phi_sig, mean_phi_sig, min_phi_sig,
                      max_prior_sig, mean_prior_sig, min_prior_sig,
                      max_theta_sig, mean_theta_sig, min_theta_sig,
                      max_x, mean_x, min_x,
                      max_theta_mu, mean_theta_mu, min_theta_mu],
               data=[Iterator(valid_data, mn_batch_size, start=2040064, end=2152704)]), #112640 is 5%
    Picklize(freq=1000, force_save_freq=10000, path=save_path),
    EarlyStopping(freq=1000, force_save_freq=10000, path=save_path),
    WeightNorm()
]

mainloop = Training(
    name='deep_m3_1',
    data=Iterator(train_data, batch_size, start=0, end=2040064),
    model=model,
    optimizer=optimizer,
    cost=nll_lower_bound,
    outputs=[nll_lower_bound],
    extension=extension
)
mainloop.run()
