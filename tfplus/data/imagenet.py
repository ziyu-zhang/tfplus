import tfplus
import os
import numpy as np
import synset
import cv2
import time
import tensorflow as tf
import tfplus
import threading

from img_preproc import ImagePreprocessor

tfplus.cmd_args.add('imagenet:dataset_folder', 'str',
                    '/ais/gobi3/datasets/imagenet')


class ImageNetDataProvider(tfplus.data.DataProvider):

    def __init__(self, split='train', folder=None, mode='train'):
        """
        Mode: train or valid or test
        Train: Random scale, random crop
        Valid: Single center crop
        Test: use 10-crop testing... Something that we haven't implemented yet.
        """
        super(ImageNetDataProvider, self).__init__()
        self.log = tfplus.utils.logger.get()
        self._split = split
        self._folder = folder
        self._img_ids = None
        self._labels = None
        self._mode = mode
        self._rnd_proc = ImagePreprocessor(
            rnd_hflip=True, rnd_colour=True, rnd_resize=[256, 480], resize=256,
            crop=224)
        self._mutex = threading.Lock()
        self.register_option('imagenet:dataset_folder')
        pass

    @property
    def folder(self):
        if self._folder is None:
            self._mutex.acquire()
            self._folder = self.get_option('imagenet:dataset_folder')
            self._mutex.release()
        return self._folder

    @property
    def split(self):
        return self._split

    @property
    def img_ids(self):
        if self._img_ids is None:
            _img_ids = []
            _labels = []
            image_folder = os.path.join(self.folder, self.split)
            if self.split == 'train':
                folders = os.listdir(image_folder)
                for ff in folders:
                    subfolder = os.path.join(image_folder, ff)
                    image_fnames = os.listdir(subfolder)
                    _img_ids.extend(image_fnames)
                    _labels.extend(
                        [synset.get_index(ff)] * len(image_fnames))
            elif self.split == 'valid' or self.split == 'test':
                _img_ids = os.listdir(image_folder)
                _img_ids = sorted(_img_ids)
                if self.split == 'valid':
                    with open(os.path.join(
                            self.folder, 'synsets.txt'), 'r') as f_cls:
                        synsets = f_cls.readlines()
                    synsets = [ss.strip('\n') for ss in synsets]
                    with open(os.path.join(
                            self.folder, 'valid_labels.txt'), 'r') as f_lab:
                        labels = f_lab.readlines()
                    labels = [int(ll) for ll in labels]
                    slabels = [synsets[ll] for ll in labels]
                    _labels = [synset.get_index(sl) for sl in slabels]
            _labels = np.array(_labels)
            self._mutex.acquire()
            self._img_ids = _img_ids
            self._labels = _labels
            self._mutex.release()
        return self._img_ids

    @property
    def labels(self):
        if self._labels is None and self.split != 'test':
            a = self.img_ids
        return self._labels

    def get_size(self):
        return len(self.img_ids)

    def get_batch_idx(self, idx, **kwargs):
        start_time = time.time()
        x = None
        y_gt = np.zeros([len(idx), 1000], dtype='float32')
        for kk, ii in enumerate(idx):
            if self.split == 'train':
                folder = os.path.join('train', self.img_ids[ii].split('_')[0])
            else:
                folder = self.split
            img_fname = os.path.join(self.folder, folder, self.img_ids[ii])
            # self.log.info('Image filename: {}'.format(img_fname))
            x_ = cv2.imread(img_fname)
            rnd = self._mode == 'train'
            x_, rnd_package = self._rnd_proc.process(x_, rnd=rnd)
            if x is None:
                x = np.zeros([len(idx), x_.shape[0], x_.shape[1], x_.shape[2]],
                             dtype='float32')
            x[kk] = x_
            y_gt[kk, self.labels[ii]] = 1.0
        results = {
            'x': x,
            'y_gt': y_gt
        }
        # self.log.info('Fetch data time: {:.4f} ms'.format(
        #               (time.time() - start_time) * 1000))
        return results
    pass


tfplus.data.data_provider.get_factory().register('imagenet',
                                                 ImageNetDataProvider)

if __name__ == '__main__':
    # print len(ImageNetDataProvider().img_ids)
    labels = ImageNetDataProvider(split='train').labels
    print labels.max()
    print labels.min()
    print len(labels)
    labels = ImageNetDataProvider(split='valid').labels
    print labels.max()
    print labels.min()
    print len(labels)
    img_ids = ImageNetDataProvider(split='valid').img_ids
    print img_ids[0]
    print img_ids[-1]
