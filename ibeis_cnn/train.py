#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Defines the models and the data we will send to the harness

CommandLine:
    python -m ibeis_cnn.train --test-train_patchmatch_pz
    python -m ibeis_cnn.train --test-train_patchmatch_pz --vtd
    python -m ibeis_cnn.train --test-train_patchmatch_pz --vtd --max-examples=5 --batch_size=128 --learning_rate .0000001
    python -m ibeis_cnn.train --test-train_patchmatch_pz --vtd --max-examples=5 --batch_size=128 --learning_rate .0000001 --verbcnn
    python -m ibeis_cnn.train --test-train_patchmatch_pz --db NNP_Master3
    python -m ibeis_cnn.train --test-train_patchmatch_pz --db NNP_Master3 --num-top=5
    python -m ibeis_cnn.train --test-train_patchmatch_pz --db NNP_Master3 --vtd
    python -m ibeis_cnn.train --test-train_patchmatch_pz --db NNP_Master3 --max-examples=1000
    python -m ibeis_cnn.train --test-train_patchmatch_pz --db NNP_Master3 --max-examples=1000 --num-top=5

TestTraining:
    python -m ibeis_cnn.train --test-train_patchmatch_pz --vtd --max-examples=5 --batch_size=128 --learning_rate .0000001
    python -m ibeis_cnn.train --test-train_patchmatch_mnist --vtd
    utprof.py -m ibeis_cnn.train --test-train_patchmatch_pz --vtd --max-examples=5 --batch_size=128 --learning_rate .0000001
    utprof.py -m ibeis_cnn.train --test-train_patchmatch_mnist --vtd

NightlyTraining:
    python -m ibeis_cnn.train --test-train_patchmatch_pz --db NNP_Master3 --max-examples=1000


TODO:
    A model architecture should have a data-agnostic directory
    Allow multiple different datasets to train the same model
      * The adjustments that that model makes should be saved in a data-specific directory
    Show bad training examples
"""
from __future__ import absolute_import, division, print_function
from ibeis_cnn import utils
from ibeis_cnn import models
from ibeis_cnn import ingest_data
from ibeis_cnn import harness
import utool as ut
print, rrr, profile = ut.inject2(__name__, '[ibeis_cnn.train]')


def train_patchmatch_pz():
    r"""

    CommandLine:
        python -m ibeis_cnn.train --test-train_patchmatch_pz --show
        python -m ibeis_cnn.train --test-train_patchmatch_pz --vtd
        python -m ibeis_cnn.train --test-train_patchmatch_pz --vtd --max-examples=5 --learning_rate .0000001

        python -m ibeis_cnn.train --test-train_patchmatch_pz --db NNP_Master3 --nocache-train
        python -m ibeis_cnn.train --test-train_patchmatch_pz --db NNP_Master3 --num-top=20
        python -m ibeis_cnn.train --test-train_patchmatch_pz --db NNP_Master3 --vtd

    Example:
        >>> # DISABLE_DOCTEST
        >>> from ibeis_cnn.train import *  # NOQA
        >>> from ibeis_cnn.harness import *  # NOQA
        >>> from ibeis_cnn.batch_processing import *  # NOQA
        >>> train_patchmatch_pz()

    Ignore:
        weights_fpath = '/media/raid/work/NNP_Master3/_ibsdb/_ibeis_cache/nets/train_patchmetric((2462)&ju%uw7bta19cunw)/ibeis_cnn_weights.pickle'
        weights_fpath = '/media/raid/work/NNP_Master3/_ibsdb/_ibeis_cache/nets/train_patchmetric((2462)&ju%uw7bta19cunw)/arch_d788de3571330d42/training_state.cPkl'
    """
    train_params = ut.argparse_dict(
        {
            'batch_size': 128,
            'learning_rate': .001,
            'momentum': .9,
            'weight_decay': 0.0005,
        }
    )
    print('[train] train_patchmatch_pz')
    # Choose data
    data_fpath, labels_fpath, training_dpath, data_shape = ingest_data.get_patchmetric_training_fpaths()

    # Choose model
    # TODO: data will need to return info about number of labels in viewpoint models
    model = models.SiameseCenterSurroundModel(data_shape=data_shape, training_dpath=training_dpath, **train_params)

    model.initialize_architecture()

    if model.has_saved_state():
        model.load_model_state()
    else:
        # Initialize with pretrained liberty weights
        # TODO: do i need to take liberty data centering as well?
        extern_training_dpath = ut.ensure_app_resource_dir('ibeis_cnn', 'training', 'liberty')
        model.load_extern_weights(dpath=extern_training_dpath)

    # Split data into subsets
    data_fpath_dict, label_fpath_dict = ingest_data.ondisk_data_split(
        model, data_fpath, labels_fpath, split_names=['train', 'valid', 'test'], fraction_list=[.2, .1])

    #ut.embed()
    if ut.get_argflag('--train'):
        config = dict(
            patience=100,
        )
        X_train, y_train = utils.load_from_fpath_dicts(data_fpath_dict, label_fpath_dict, 'train')
        X_valid, y_valid = utils.load_from_fpath_dicts(data_fpath_dict, label_fpath_dict, 'valid')
        #X_test, y_test = utils.load_from_fpath_dicts(data_fpath_dict, label_fpath_dict, 'test')
        harness.train(model, X_train, y_train, X_valid, y_valid, config)
    elif ut.get_argflag('--test'):
        assert model.best_results['epoch'] is not None
        X_test, y_test = utils.load_from_fpath_dicts(data_fpath_dict, label_fpath_dict, 'test')
        harness.test(model, X_test, y_test, **config)
    else:
        raise NotImplementedError('nothing here. need to train or test')


def train_patchmatch_liberty():
    r"""
    CommandLine:
        python -m ibeis_cnn.train --test-train_patchmatch_liberty --show
        python -m ibeis_cnn.train --test-train_patchmatch_liberty --vtd
        python -m ibeis_cnn.train --test-train_patchmatch_liberty --show --test

    Example:
        >>> # ENABLE_DOCTEST
        >>> from ibeis_cnn.train import *  # NOQA
        >>> result = train_patchmatch_liberty()
        >>> ut.show_if_requested()
        >>> print(result)
    """
    #pairs = 500
    pairs = 250000
    data_fpath, labels_fpath, training_dpath, data_shape = ingest_data.grab_cached_liberty_data(pairs)
    #model = models.SiameseModel()
    model = models.SiameseCenterSurroundModel(data_shape=data_shape, training_dpath=training_dpath)

    model.initialize_architecture()
    # DO CONVERSION
    if False:
        old_weights_fpath = ut.truepath('~/Dropbox/ibeis_cnn_weights_liberty.pickle')
        if ut.checkpath(old_weights_fpath, verbose=True):
            self = model
            self.load_old_weights_kw(old_weights_fpath)
        self.save_model_state()
        #self.save_state()

    if model.has_saved_state():
        model.load_model_state()
        print(model.get_state_str())
    else:
        model.reinit_weights()

    # Split data into subsets
    data_fpath_dict, label_fpath_dict = ingest_data.ondisk_data_split(
        model, data_fpath, labels_fpath, split_names=['train', 'valid', 'test'], fraction_list=[.2, .1])

    #ut.embed()
    if ut.get_argflag('--train'):
        config = dict(
            patience=100,
        )
        X_train, y_train = utils.load_from_fpath_dicts(data_fpath_dict, label_fpath_dict, 'train')
        X_valid, y_valid = utils.load_from_fpath_dicts(data_fpath_dict, label_fpath_dict, 'valid')
        #X_test, y_test = utils.load_from_fpath_dicts(data_fpath_dict, label_fpath_dict, 'test')
        harness.train(model, X_train, y_train, X_valid, y_valid, config)
    elif ut.get_argflag('--test'):
        from ibeis_cnn import experiments

        X_test, y_test = utils.load_from_fpath_dicts(data_fpath_dict, label_fpath_dict, 'test')
        X_test, y_test = utils.random_test_train_sample(X_test, y_test, 1000, model.data_per_label)

        # TEST SIFT DISTANCE
        #experiments.test_sift_patchmatch(X_test, y_test)
        # TEST CNN DISTANCE
        test_outputs = harness.test_data2(model, X_test, y_test)
        #ut.embed()
        network_output = test_outputs['network_output']
        scores = network_output.T[0]
        labels = y_test

        experiments.test_siamese_thresholds(network_output, y_test, figtitle='CNN descriptor distances')

        model.learn_encoder(scores, y_test)
    else:
        raise NotImplementedError('nothing here. need to train or test')


def train_mnist():
    r"""
    CommandLine:
        python -m ibeis_cnn.train --test-train_mnist

    Example:
        >>> # DISABLE_DOCTEST
        >>> from ibeis_cnn.train import *  # NOQA
        >>> result = train_mnist()
        >>> print(result)
    """
    train_params = ut.argparse_dict(
        {
            'batch_size': 128,
            'learning_rate': .001,
            'momentum': .9,
            'weight_decay': 0.0005,
        }
    )
    data_fpath, labels_fpath, training_dpath, data_shape, output_dims = ingest_data.grab_cached_mist_data()
    input_shape = (None, data_shape[2], data_shape[0], data_shape[1])

    # Choose model
    model = models.MNISTModel(
        input_shape=input_shape, output_dims=output_dims,
        training_dpath=training_dpath, **train_params)

    # Initialize architecture
    model.initialize_architecture()

    # Load previously learned weights or initialize new weights
    if model.has_saved_state():
        model.load_model_state()
    else:
        model.reinit_weights()

    config = dict(
        patience=100,
        show_confusion=False,
        run_test=None,
        show_features=False,
        print_timing=False,
    )
    # Split data into subsets
    data_fpath_dict, label_fpath_dict = ingest_data.ondisk_data_split(
        model, data_fpath, labels_fpath, split_names=['train', 'valid', 'test'], fraction_list=[.5, .5])

    X_train, y_train = utils.load_from_fpath_dicts(data_fpath_dict, label_fpath_dict, 'train')
    X_valid, y_valid = utils.load_from_fpath_dicts(data_fpath_dict, label_fpath_dict, 'valid')
    #X_test, y_test = utils.load_from_fpath_dicts(data_fpath_dict, label_fpath_dict, 'test')
    harness.train(model, X_train, y_train, X_valid, y_valid, config)


if __name__ == '__main__':
    """
    CommandLine:
        python -m ibeis_cnn.train
        python -m ibeis_cnn.train --allexamples
        python -m ibeis_cnn.train --allexamples --noface --nosrc
    """
    #train_pz()
    import multiprocessing
    multiprocessing.freeze_support()  # for win32
    import utool as ut  # NOQA
    #import warnings
    #with warnings.catch_warnings():
    #    # Cause all warnings to always be triggered.
    #    warnings.filterwarnings("error", ".*get_all_non_bias_params.*")
    ut.doctest_funcs()
