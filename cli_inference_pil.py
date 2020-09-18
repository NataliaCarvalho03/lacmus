#!/usr/bin/env python
import keras
# import keras_retinanet
import tensorflow as tf
import keras_retinanet
from keras_retinanet import models, losses
# import miscellaneous modules
import PIL
from PIL import Image
import argparse
import sys
import os
import numpy as np
import time
import json


def parse_args(args):
    parser = argparse.ArgumentParser(description='convert model')
    parser.add_argument(
        '--img',
        help='path to image',
        type=str,
        required=True
    )
    parser.add_argument(
        '--bin',
        help='path to h5 keras inference model',
        type=str,
        required=True
    )
    parser.add_argument(
        '--backbone',
        help='backbone name',
        type=str,
        required=False,
        default='resnet50'
    )
    parser.add_argument(
        '--count',
        help='iference count',
        type=int,
        required=False,
        default=3
    )
    parser.add_argument(
        '--gpu',
        help='use gpu',
        action='store_true',
        required=False,
    )
    parser.add_argument(
        '--out',
        help='save output',
        type=str,
        required=False
    )
    return parser.parse_args(args)

def compute_resize_scale(image_shape, min_side=800, max_side=1333):
    """ Compute an image scale such that the image size is constrained to min_side and max_side.

    Args
        min_side: The image's min side will be equal to min_side after resizing.
        max_side: If after resizing the image's max side is above max_side, resize until the max side is equal to max_side.

    Returns
        A resizing scale.
    """
    (rows, cols, _) = image_shape

    smallest_side = min(rows, cols)

    # rescale the image so the smallest side is min_side
    scale = min_side / smallest_side

    # check if the largest side is now greater than max_side, which can happen
    # when images have a large aspect ratio
    largest_side = max(rows, cols)
    if largest_side * scale > max_side:
        scale = max_side / largest_side

    return scale

def preprocess_image(x, mode='caffe'):
    """ Preprocess an image by subtracting the ImageNet mean.

    Args
        x: np.array of shape (None, None, 3) or (3, None, None).
        mode: One of "caffe" or "tf".
            - caffe: will zero-center each color channel with
                respect to the ImageNet dataset, without scaling.
            - tf: will scale pixels between -1 and 1, sample-wise.

    Returns
        The input with the ImageNet mean subtracted.
    """
    # mostly identical to "https://github.com/keras-team/keras-applications/blob/master/keras_applications/imagenet_utils.py"
    # except for converting RGB -> BGR since we assume BGR already

    # covert always to float32 to keep compatibility with opencv
    x = x.astype(np.float32)

    if mode == 'tf':
        x /= 127.5
        x -= 1.
    elif mode == 'caffe':
        x[..., 0] -= 103.939
        x[..., 1] -= 116.779
        x[..., 2] -= 123.68

    return x

def read_image_bgr(path, min_side=800, max_side=1333):
    """ Read an image in BGR format.

    Args
        path: Path to the image.
    """
    img = Image.open(path).convert('RGB')
    scale = compute_resize_scale(np.ascontiguousarray(img).shape, min_side=min_side, max_side=max_side)
    img = img.resize( [int(scale * s) for s in img.size] )
    image = np.ascontiguousarray(img)
    return image[:, :, ::-1], scale

def setup_gpu(gpu_id: int):
    if gpu_id == -1:
        tf.config.experimental.set_visible_devices([], 'GPU')
        return

    gpus = tf.config.experimental.list_physical_devices('GPU')
    if gpus:
        try:
            tf.config.experimental.set_virtual_device_configuration(
                gpus[gpu_id],
                [tf.config.experimental.VirtualDeviceConfiguration(memory_limit=2048)])
            logical_gpus = tf.config.experimental.list_logical_devices('GPU')
            print(len(gpus), "Physical GPUs,", len(logical_gpus), "Logical GPUs")
        except RuntimeError as e:
            print(e)

def main(args=None):
    args=parse_args(args)

    model_bin = args.bin
    img_fn = args.img
    predict_count = args.count
    backbone = args.backbone

    print("loading model...")
    if args.gpu:
        setup_gpu(0)

    model = models.load_model(model_bin, backbone_name=backbone)

    print(f'model input shape: {model.inputs[0].shape}')

    start_time = time.time()

    image, scale = read_image_bgr(img_fn)
    image = preprocess_image(image)
    print("prepoocess image at {} s".format(time.time() - start_time))
    return

    labels_to_names = {0: 'Pedestrian'}

    print(f'make {predict_count} predictions:')
    for _ in range(0, predict_count):
        start_time = time.time()
        boxes, scores, labels = model.predict_on_batch(np.expand_dims(image, axis=0))
        print("\t{} s".format(time.time() - start_time))

    
    print("*"*20)
    print('bboxes:', boxes.shape)
    print('scores:', scores.shape)
    print('labels:', labels.shape)

    boxes /= scale

    objects_count = 0

    print("*"*20)
    for box, score, label in zip(boxes[0], scores[0], labels[0]):
        # scores are sorted so we can break
        if score < 0.5:
            break
        b = np.array(box.astype(int)).astype(int)
        # x1 y1 x2 y2
        print(f'{labels_to_names[label]}:')
        print(f'\tscore: {score}')
        print(f'\tbox: {b[0]} {b[1]} {b[2]} {b[3]}')
        objects_count = objects_count + 1
    print(f'found objects: {objects_count}')

    if args.out:
        model.save(args.out)


if __name__ == '__main__':
    main()