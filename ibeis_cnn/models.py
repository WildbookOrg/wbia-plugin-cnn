# -*- coding: utf-8 -*-
"""
file model.py
allows the definition of different models to be trained
for initialization: Lasagne/lasagne/init.py
for nonlinearities: Lasagne/lasagne/nonlinearities.py
for layers: Lasagne/lasagne/layers/
"""
from __future__ import absolute_import, division, print_function
import lasagne  # NOQA
from lasagne import layers
from lasagne import nonlinearities
from lasagne import init
import functools
import six
import theano.tensor as T
import numpy as np
from ibeis_cnn import abstract_models
from ibeis_cnn import custom_layers
from ibeis_cnn import augment
import utool as ut
print, rrr, profile = ut.inject2(__name__, '[ibeis_cnn.models]')
#from ibeis_cnn import utils
#import sklearn.preprocessing
#import cPickle as pickle
# from os.path import join
# import cPickle as pickle

Conv2DLayer = custom_layers.Conv2DLayer
MaxPool2DLayer = custom_layers.MaxPool2DLayer


@six.add_metaclass(ut.ReloadingMetaclass)
class SiameseCenterSurroundModel(abstract_models.BaseModel):
    """
    Model for individual identification

    TODO:
        RBM / EBM  - http://deeplearning.net/tutorial/rbm.html
    """
    def __init__(model, autoinit=False, batch_size=128, input_shape=None, data_shape=None, **kwargs):
        if data_shape is not None:
            input_shape = (batch_size, data_shape[2], data_shape[0], data_shape[1])
        if input_shape is None:
            (batch_size, 3, 64, 64)
        super(SiameseCenterSurroundModel, model).__init__(input_shape=input_shape, batch_size=batch_size, **kwargs)
        #model.network_layers = None
        model.input_shape = input_shape
        model.batch_size = batch_size
        model.output_dims = 1
        # bad name, says that this network will take
        # 2*N images in a batch and N labels that map to
        # two images a piece
        model.data_per_label = 2
        if autoinit:
            model.initialize_architecture()

    def build_model(model, batch_size, input_width, input_height,
                    input_channels, output_dims, verbose=True, **kwargs):
        r"""
        """
        #print('build model may override settings')
        input_shape = (batch_size, input_channels, input_width, input_height)
        model.input_shape = input_shape
        model.batch_size = batch_size
        model.output_dims = 1
        model.initialize_architecture(verbose=verbose, **kwargs)
        output_layer = model.get_output_layer()
        return output_layer

    def augment(self, Xb, yb=None):
        Xb, yb = augment.augment_siamese_patches2(Xb, yb)

    def get_2ch2stream_def(model, verbose=True, **kwargs):
        """
        Notes:

            (i) 2ch-2stream consists of two branches
                C(95, 5, 1)- ReLU-
                P(2, 2)-
                C(96, 3, 1)- ReLU-
                P(2, 2)-
                C(192, 3, 1)- ReLU-
                C(192, 3, 1)- ReLU,

                one for central and one for surround parts, followed by
                F(768)- ReLU-
                F(1)
        """
        raise NotImplementedError('The 2-channel part is not yet implemented')
        _P = functools.partial
        leaky_kw = dict(nonlinearity=nonlinearities.LeakyRectify(leakiness=(1. / 10.)))
        orthog_kw = dict(W=init.Orthogonal())
        hidden_initkw = ut.merge_dicts(orthog_kw, leaky_kw)

        network_layers_def = (
            [
                _P(layers.InputLayer, shape=model.input_shape),
                # TODO: Stack Inputs by making a 2 Channel Layer
                _P(custom_layers.CenterSurroundLayer),

                #layers.GaussianNoiseLayer,
                #caffenet.get_conv2d_layer(0, trainable=False, **leaky),
                #lasange_ext.freeze_params,
                _P(Conv2DLayer, num_filters=96, filter_size=(5, 5), stride=(1, 1), name='C0', **hidden_initkw),
                _P(MaxPool2DLayer, pool_size=(2, 2), stride=(2, 2), name='P0'),
                _P(Conv2DLayer, num_filters=96, filter_size=(3, 3), name='C1', **hidden_initkw),
                _P(MaxPool2DLayer, pool_size=(2, 2), stride=(2, 2), name='P1'),
                _P(Conv2DLayer, num_filters=192, filter_size=(3, 3), name='C2', **hidden_initkw),
                _P(Conv2DLayer, num_filters=192, filter_size=(3, 3), name='C3', **hidden_initkw),
                #_P(custom_layers.L2NormalizeLayer, axis=2),
                _P(custom_layers.SiameseConcatLayer, axis=1, data_per_label=4),  # 4 when CenterSurroundIsOn
                #_P(custom_layers.SiameseConcatLayer, data_per_label=2),
                _P(layers.DenseLayer, num_units=768, name='F1',  **hidden_initkw),
                _P(layers.DropoutLayer, p=0.5),
                _P(layers.DenseLayer, num_units=1, name='F2', **hidden_initkw),
            ]
        )
        return network_layers_def

    def get_siam2stream_def(model, verbose=True, **kwargs):
        """
        Notes:
            (viii) siam-2stream has 4 branches
                C(96, 4, 2)- ReLU-
                P(2, 2)-
                C(192, 3, 1)- ReLU-
                C(256, 3, 1)- ReLU-
                C(256, 3, 1)- ReLU

                (coupled in pairs for central and surround streams, and decision layer)

                F(512)-ReLU-
                F(1)
        """
        _P = functools.partial

        leaky_kw = dict(nonlinearity=nonlinearities.LeakyRectify(leakiness=(1. / 10.)))
        orthog_kw = dict(W=init.Orthogonal())
        hidden_initkw = ut.merge_dicts(orthog_kw, leaky_kw)
        if not kwargs.get('fresh_model', False):
            # FIXME: figure out better way of encoding that Orthogonal
            # Initialization doesnt need to happen. Or do initialization of
            # weights after the network has been built.
            # don't do fancy initializating unless training from scratch
            del hidden_initkw['W']

        network_layers_def = (
            [
                _P(layers.InputLayer, shape=model.input_shape),
                # TODO: Stack Inputs by making a 2 Channel Layer
                _P(custom_layers.CenterSurroundLayer),

                layers.GaussianNoiseLayer,
                #caffenet.get_conv2d_layer(0, trainable=False, **leaky),
                _P(Conv2DLayer, num_filters=96, filter_size=(4, 4), name='C0', **hidden_initkw),
                _P(MaxPool2DLayer, pool_size=(2, 2), stride=(2, 2), name='P0'),
                _P(Conv2DLayer, num_filters=192, filter_size=(3, 3), name='C2', **hidden_initkw),
                _P(Conv2DLayer, num_filters=256, filter_size=(3, 3), name='C3', **hidden_initkw),
                _P(Conv2DLayer, num_filters=256, filter_size=(3, 3), name='C3', **hidden_initkw),
                #_P(custom_layers.L2NormalizeLayer, axis=2),
                _P(custom_layers.SiameseConcatLayer, axis=1, data_per_label=4),  # 4 when CenterSurroundIsOn
                #_P(custom_layers.SiameseConcatLayer, data_per_label=2),
                _P(layers.DenseLayer, num_units=512, name='F1',  **hidden_initkw),
                _P(layers.DropoutLayer, p=0.5),
                _P(layers.DenseLayer, num_units=1, name='F2', **hidden_initkw),
            ]
        )
        #raise NotImplementedError('The 2-channel part is not yet implemented')
        return network_layers_def

    def initialize_architecture(model, verbose=True, **kwargs):
        r"""
        Notes:
            http://arxiv.org/pdf/1504.03641.pdf

            Performance of several models on the local image patches benchmark.
            The shorthand notation used was the following.
            C(n, k, s) is a convolutional layer with n filters of spatial size k x k applied with stride s.
            P(k, s) is a max-pooling layer of size k x k applied with stride s.
            F(n) denotes a fully connected linear layer with n output
            units.
            The models architecture is as follows:

            (ii)
                2ch-deep =
                    C(96, 4, 3)- Stack(96)- P(2, 2)- Stack(192)- F(1),
                Stack(n) =
                    C(n, 3, 1)- ReLU- C(n, 3, 1)- ReLU- C(n, 3, 1)- ReLU.

            (iii)
                2ch =
                    C(96, 7, 3)- ReLU- P(2, 2)- C(192, 5, 1)- ReLU- P(2, 2)- C(256, 3, 1)- ReLU- F(256)- ReLU- F(1)

            (iv)
                siam has two branches
                    C(96, 7, 3)- ReLU- P(2, 2)- C(192, 5, 1)- ReLU- P(2, 2)- C(256, 3, 1)- ReLU
                and decision layer
                    F(512)- ReLU- F(1)

            (v) siam-l2 reduces to a single branch of siam

            (vi) pseudo-siam is uncoupled version of siam

            (vii) pseudo-siam-l2 reduces to a single branch of pseudo-siam

            (ix) siam-2stream-l2 consists of one central and one surround
                branch of siam-2stream.

        CommandLine:
            python -m ibeis_cnn.models --test-SiameseCenterSurroundModel.initialize_architecture
            python -m ibeis_cnn.models --test-SiameseCenterSurroundModel.initialize_architecture --verbcnn
            python -m ibeis_cnn.train --test-train_patchmatch_pz --vtd --max-examples=5 --batch_size=128 --learning_rate .0000001 --verbcnn
            python -m ibeis_cnn.train --test-train_patchmatch_pz --vtd

        Example:
            >>> # ENABLE_DOCTEST
            >>> from ibeis_cnn.models import *  # NOQA
            >>> # build test data
            >>> batch_size = 128
            >>> input_shape = (batch_size, 3, 64, 64)
            >>> verbose = True
            >>> model = SiameseCenterSurroundModel(batch_size=batch_size, input_shape=input_shape)
            >>> # execute function
            >>> output_layer = model.initialize_architecture()
            >>> print('\n---- Arch Str')
            >>> model.print_architecture_str(sep='\n')
            >>> print('\n---- Layer Info')
            >>> model.print_layer_info()
            >>> print('\n---- HashID')
            >>> print('hashid=%r' % (model.get_architecture_hashid()),)
            >>> print('----')
            >>> # verify results
            >>> result = str(output_layer)
            >>> print(result)

        """
        # TODO: remove output dims
        #_P = functools.partial
        (_, input_channels, input_width, input_height) = model.input_shape
        if verbose:
            print('[model] Initialize center surround siamese model architecture')
            print('[model]   * batch_size     = %r' % (model.batch_size,))
            print('[model]   * input_width    = %r' % (input_width,))
            print('[model]   * input_height   = %r' % (input_height,))
            print('[model]   * input_channels = %r' % (input_channels,))
            print('[model]   * output_dims    = %r' % (model.output_dims,))

        network_layers_def = model.get_siam2stream_def(verbose=verbose, **kwargs)

        # connect and record layers
        network_layers = abstract_models.evaluate_layer_list(network_layers_def)
        #model.network_layers = network_layers
        output_layer = network_layers[-1]
        model.output_layer = output_layer
        return output_layer

    def loss_function(model, network_output, Y, T=T, verbose=True):
        """

        CommandLine:
            python -m ibeis_cnn.models --test-loss_function
            python -m ibeis_cnn.models --test-loss_function:1 --show

        Example:
            >>> # ENABLE_DOCTEST
            >>> from ibeis_cnn.models import *  # NOQA
            >>> from ibeis_cnn import ingest_data
            >>> from ibeis_cnn import batch_processing as batch
            >>> data, labels = ingest_data.testdata_patchmatch()
            >>> model = SiameseCenterSurroundModel(autoinit=True, input_shape=(128,) + (data.shape[1:]))
            >>> theano_forward = batch.create_unbuffered_network_output_func(model)
            >>> batch_size = model.batch_size
            >>> Xb, yb = data[0:batch_size * model.data_per_label], labels[0:batch_size]
            >>> network_output = theano_forward(Xb)[0]
            >>> network_output = network_output
            >>> Y = yb
            >>> T = np
            >>> # execute function
            >>> verbose = True
            >>> avg_loss = model.loss_function(network_output, Y, T=T)
            >>> result = str(avg_loss)
            >>> print(result)

        Example1:
            >>> # ENABLE_DOCTEST
            >>> from ibeis_cnn.models import *  # NOQA
            >>> network_output = np.linspace(-2, 2, 128)
            >>> Y0 = np.zeros(len(network_output), np.float32)
            >>> Y1 = np.ones(len(network_output), np.float32)
            >>> verbose = False
            >>> T = np
            >>> Y = Y0
            >>> loss0, Y0_ = ut.exec_func_sourcecode(SiameseCenterSurroundModel.loss_function, globals(), locals(), ['loss', 'Y_'])
            >>> Y = Y1
            >>> loss1, Y1_ = ut.exec_func_sourcecode(SiameseCenterSurroundModel.loss_function, globals(), locals(), ['loss', 'Y_'])
            >>> assert np.all(Y1 == 1), 'bad label mapping'
            >>> assert np.all(Y0 == 0), 'bad label mapping'
            >>> assert np.all(Y0_ == -1), 'bad label mapping'
            >>> assert np.all(Y1_ == 1), 'bad label mapping'
            >>> ut.quit_if_noshow()
            >>> import plottool as pt
            >>> pt.plot2(network_output, loss0, '-', color=pt.TRUE_BLUE, label='imposter_loss', y_label='network output')
            >>> pt.plot2(network_output, loss1, '-', color=pt.FALSE_RED, label='genuine_loss', y_label='network output')
            >>> pt.legend()
            >>> ut.show_if_requested()
        """
        if verbose:
            print('[model] Build SiameseCenterSurroundModel loss function')
        # make y_i in {-1, 1} where -1 denotes non-matching and +1 denotes matching
        #Y_ = (1 - (2 * Y))
        Y_ = ((2 * Y) - 1)
        # Hinge-loss objective from Zagoruyko and Komodakis
        loss = T.maximum(0, 1 - (Y_ * network_output.T))
        avg_loss = T.mean(loss)
        if T is not np:
            loss.name = 'loss'
            avg_loss.name = 'avg_loss'
        return avg_loss

    def learn_encoder(model, labels, scores, **kwargs):
        import vtool as vt
        encoder = vt.ScoreNormalizer(**kwargs)
        encoder.fit(scores, labels)
        print('[model] learned encoder accuracy = %r' % (encoder.get_accuracy(scores, labels)))
        model.encoder = encoder
        return encoder

    #def build_objective(self):
    #    pass

    #def build_regularized_objective(self, loss, output_layer, regularization):
    #    """ L2 weight decay """
    #    import warnings
    #    with warnings.catch_warnings():
    #        warnings.filterwarnings('ignore', '.*get_all_non_bias_params.*')
    #        L2 = lasagne.regularization.l2(output_layer)
    #        regularized_loss = L2 * regularization
    #        regularized_loss.name = 'regularized_loss'
    #    return regularized_loss

        #avg_loss = lasange_ext.siamese_loss(G, Y_padded, data_per_label=2)
        #return avg_loss


class MNISTModel(abstract_models.AbstractCategoricalModel):
    """
    Toy model for testing and playing with mnist
    """
    def __init__(self, **kwargs):
        super(MNISTModel, self).__init__(**kwargs)

    def get_mnist_model_def1(model, input_shape, output_dims):
        _P = functools.partial
        leaky = dict(nonlinearity=nonlinearities.LeakyRectify(leakiness=(1. / 10.)))
        #orthog = dict(W=init.Orthogonal())
        weight_initkw = dict()
        output_initkw = weight_initkw
        hidden_initkw = ut.merge_dicts(weight_initkw, leaky)

        network_layers_def = (
            [
                _P(layers.InputLayer, shape=input_shape),
                layers.GaussianNoiseLayer,

                _P(Conv2DLayer, num_filters=32, filter_size=(5, 5), stride=(1, 1), name='C0', **hidden_initkw),
                _P(layers.DropoutLayer, p=0.1),
                _P(MaxPool2DLayer, pool_size=(2, 2), stride=(2, 2), name='P0'),

                _P(Conv2DLayer, num_filters=32, filter_size=(5, 5), stride=(1, 1), name='C1', **hidden_initkw),
                _P(MaxPool2DLayer, pool_size=(2, 2), stride=(2, 2), name='P1'),

                _P(layers.DenseLayer, num_units=256, name='F1',  **hidden_initkw),
                _P(layers.FeaturePoolLayer, pool_size=2),  # maxout
                _P(layers.DropoutLayer, p=0.5),

                _P(layers.DenseLayer, num_units=output_dims,
                   nonlinearity=nonlinearities.softmax, **output_initkw)
            ]
        )
        return network_layers_def

    def get_mnist_model_def_failure(model, input_shape, output_dims):
        # causes failure in building model
        _P = functools.partial
        leaky = dict(nonlinearity=nonlinearities.LeakyRectify(leakiness=(1. / 10.)))
        orthog = dict(W=init.Orthogonal())
        hidden_initkw = ut.merge_dicts(orthog, leaky)
        initkw = hidden_initkw
        #initkw = {}

        # def to test failures
        network_layers_def = (
            [
                _P(layers.InputLayer, shape=input_shape),
                #layers.GaussianNoiseLayer,

                _P(Conv2DLayer, num_filters=16, filter_size=(7, 7), stride=(1, 1), name='C0', **initkw),
                _P(MaxPool2DLayer, pool_size=(3, 3), stride=(3, 3), name='P0'),
                _P(Conv2DLayer, num_filters=16, filter_size=(3, 3), stride=(1, 1), name='C1', **initkw),
                _P(Conv2DLayer, num_filters=16, filter_size=(3, 3), stride=(1, 1), name='C2', **initkw),
                _P(Conv2DLayer, num_filters=16, filter_size=(3, 3), stride=(1, 1), name='C3', **initkw),
                _P(Conv2DLayer, num_filters=16, filter_size=(2, 2), stride=(1, 1), name='C4', **initkw),
                _P(Conv2DLayer, num_filters=16, filter_size=(1, 1), stride=(1, 1), name='C5', **initkw),
                _P(Conv2DLayer, num_filters=16, filter_size=(2, 2), stride=(1, 1), name='C6', **initkw),

                _P(layers.DenseLayer, num_units=32, name='F1',  **initkw),
                _P(layers.DenseLayer, num_units=output_dims, nonlinearity=nonlinearities.softmax)
            ]
        )
        return network_layers_def

    def initialize_architecture(self):
        input_shape = self.input_shape
        output_dims = self.output_dims
        network_layers_def = self.get_mnist_model_def1(input_shape, output_dims)
        network_layers = abstract_models.evaluate_layer_list(network_layers_def)
        self.output_layer = network_layers[-1]
        return self.output_layer


@six.add_metaclass(ut.ReloadingMetaclass)
class DummyModel(abstract_models.AbstractCategoricalModel):
    def __init__(model, autoinit=False, batch_size=8, input_shape=None, **kwargs):
        #if data_shape is not None:
        #    input_shape = (batch_size, data_shape[2], data_shape[0], data_shape[1])
        if input_shape is None:
            input_shape = (None, 1, 4, 4)
        super(DummyModel, model).__init__(input_shape=input_shape, batch_size=batch_size, **kwargs)
        #model.network_layers = None
        model.data_per_label = 1
        model.input_shape = input_shape
        model.output_dims = 5
        #model.batch_size = 8
        #model.learning_rate = .001
        #model.momentum = .9
        if autoinit:
            model.initialize_architecture()

    def make_random_testdata(model, num=1000, seed=0):
        np.random.seed(seed)
        X_unshared = np.random.rand(num, * model.input_shape[1:]).astype(np.float32)
        y_unshared = (np.random.rand(num) * model.output_dims).astype(np.int32)
        if ut.VERBOSE:
            print('made random testdata')
            print('size(X_unshared) = %r' % (ut.get_object_size_str(X_unshared),))
            print('size(y_unshared) = %r' % (ut.get_object_size_str(y_unshared),))
        return X_unshared, y_unshared

    def make_prediction_expr(model, newtork_output):
        prediction = T.argmax(newtork_output, axis=1)
        prediction.name = 'prediction'
        return prediction

    def make_accuracy_expr(model, prediction, y_batch):
        accuracy = T.mean(T.eq(prediction, y_batch))
        accuracy.name = 'accuracy'
        return accuracy

    #def get_loss_function(model):
    #    return T.nnet.categorical_crossentropy

    def initialize_architecture(model, verbose=True):
        input_shape = model.input_shape
        _P = functools.partial
        network_layers_def = [
            _P(layers.InputLayer, shape=input_shape),
            _P(Conv2DLayer, num_filters=16, filter_size=(3, 3)),
            _P(Conv2DLayer, num_filters=16, filter_size=(2, 2)),
            _P(layers.DenseLayer, num_units=8),
            _P(layers.DenseLayer, num_units=model.output_dims,
               nonlinearity=nonlinearities.softmax,
               W=init.Orthogonal(),),
        ]
        network_layers = abstract_models.evaluate_layer_list(network_layers_def)
        #model.network_layers = network_layers
        model.output_layer = network_layers[-1]
        if verbose:
            print('initialize_architecture')
        if ut.VERBOSE:
            model.print_architecture_str()
            model.print_layer_info()
        return model.output_layer

    #def initialize_symbolic_inputs(model):
    #    model.symbolic_index = T.lscalar(name='index')
    #    model.symbolic_X = T.tensor4(name='X')
    #    model.symbolic_y = T.ivector(name='y')

    #def initialize_symbolic_updates(model):
    #    pass

    #def initialize_symbolic_outputs(model):
    #    pass


if __name__ == '__main__':
    """
    CommandLine:
        python -m ibeis_cnn.models
        python -m ibeis_cnn.models --allexamples
        python -m ibeis_cnn.models --allexamples --noface --nosrc
    """
    import multiprocessing
    multiprocessing.freeze_support()  # for win32
    import utool as ut  # NOQA
    ut.doctest_funcs()
