from __future__ import division

import cv2
import numpy as np
import tensorflow as tf


class ImagePreprocessor(object):

    def __init__(self, resize, rnd_hflip, rnd_resize, crop, rnd_colour):
        """
        """
        self._random = np.random.RandomState(2)
        # readonly
        self._rnd_resize = rnd_resize
        # readonly
        self._rnd_hflip = rnd_hflip
        # readonly
        self._resize = resize
        # readonly
        self.crop = crop
        # readonly
        self._rnd_colour = rnd_colour
        self._image_in, self._image_out = self.build_colour_graph()
        self._sess = tf.Session()
        pass

    @property
    def crop(self):
        return self._crop

    @property
    def resize(self):
        return self._resize

    @property
    def rnd_hflip(self):
        return self._rnd_hflip

    @property
    def rnd_resize(self):
        return self._rnd_resize

    @property
    def random(self):
        return self._random

    @property
    def rnd_colour(self):
        return self._rnd_colour

    @property
    def image_in(self):
        return self._image_in

    @property
    def image_out(self):
        return self._image_out

    @property
    def sess(self):
        return self._sess

    def build_colour_graph(self):
        """Build random colour graph."""
        device = '/cpu:0'
        with tf.device(device):
            image_in = tf.placeholder('float', [None, None, 3])
            image_out = image_in
            image_out = tf.image.random_brightness(
                image_out, max_delta=32. / 255.)
            image_out = tf.image.random_saturation(
                image_out, lower=0.5, upper=1.5)
            image_out = tf.image.random_hue(image_out, max_delta=0.1)
            image_out = tf.image.random_contrast(
                image_out, lower=0.5, upper=1.5)
            image_out = tf.clip_by_value(image_out, 0.0, 1.0)
        return image_in, image_out

    def redraw(self, height, width):
        siz = int(self.random.uniform(self.rnd_resize[0], self.rnd_resize[1]))
        short = min(width, height)
        lon = max(width, height)
        if width < height:
            siz2 = (siz, int(height / width * siz))
        else:
            siz2 = (int(width / height * siz), siz)
        offset = [0.0, 0.0]
        offset[0] = int(self.random.uniform(0.0, siz2[0] - self.crop))
        offset[1] = int(self.random.uniform(0.0, siz2[1] - self.crop))
        hflip = bool(self.random.uniform(0, 1))

        return {
            'offset': offset,
            'siz2': siz2,
            'hflip': hflip
        }
        pass

    def process(self, image, rnd=True, rnd_package=None):
        """Process the images.

        redraw: Whether to redraw random numbers used for random cropping, and
        horizontal flipping. Random colours have to be redrawn.
        """
        # BGR => RGB
        image = image[:, :, [2, 1, 0]]
        image = (image / 255).astype('float32')
        width = image.shape[1]
        height = image.shape[0]

        if rnd_package is None:
            rnd_package = self.redraw(height=height, width=width)

        offset_ = rnd_package['offset']
        siz2_ = rnd_package['siz2']
        hflip_ = rnd_package['hflip']

        if rnd:
            siz2 = siz2_
            offset = offset_
            hflip = hflip_ and self.rnd_hflip
        else:
            siz = self.resize
            short = min(width, height)
            lon = max(width, height)
            if width < height:
                siz2 = (siz, int(height / width * siz))
            else:
                siz2 = (int(width / height * siz), siz)
            offset = [0, 0]
            offset[0] = int((siz2[0] - self.crop) / 2)
            offset[1] = int((siz2[1] - self.crop) / 2)
            hflip = False

        if siz2[0] < self.crop + offset[0] or siz2[1] < self.crop + offset[1]:
            raise Exception('Invalid siz2 {}, {}'.format(siz2, offset))

        image = cv2.resize(image, siz2, interpolation=cv2.INTER_CUBIC)
        image = image[offset[1]: self.crop + offset[1],
                      offset[0]: self.crop + offset[0], :]

        if hflip:
            image = np.fliplr(image)

        if rnd and self.rnd_colour and image.shape[-1] == 3:
            image = self.sess.run(self.image_out, feed_dict={
                                  self.image_in: image})
        # RGB => BGR
        image = image[:, :, [2, 1, 0]]

        return image, rnd_package
