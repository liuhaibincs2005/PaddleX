import os
os.environ['CUDA_VISIBLE_DEVICES'] = '0'

import paddlex as pdx
from paddlex import transforms

dataset = 'https://bj.bcebos.com/paddlex/datasets/insect_det.tar.gz'
pdx.utils.download_and_decompress(dataset, path='./')

train_transforms = transforms.Compose([
    transforms.MixupImage(mixup_epoch=250), transforms.RandomDistort(),
    transforms.RandomExpand(im_padding_value=[123.675, 116.28, 103.53]),
    transforms.RandomCrop(), transforms.RandomHorizontalFlip(),
    transforms.BatchRandomResize(
        target_sizes=[320, 352, 384, 416, 448, 480, 512, 544, 576, 608],
        interp='RANDOM'), transforms.Normalize(
            mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

eval_transforms = transforms.Compose([
    transforms.Resize(
        608, interp='CUBIC'), transforms.Normalize(
            mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

train_dataset = pdx.datasets.VOCDetection(
    data_dir='insect_det',
    file_list='insect_det/train_list.txt',
    label_list='insect_det/labels.txt',
    transforms=train_transforms,
    shuffle=True)

eval_dataset = pdx.datasets.VOCDetection(
    data_dir='insect_det',
    file_list='insect_det/val_list.txt',
    label_list='insect_det/labels.txt',
    transforms=eval_transforms,
    shuffle=False)

model = pdx.load_model('output/yolov3_darknet53/best_model')

# Step 1/3: 分析模型各层参数在不同的剪裁比例下的敏感度
# API说明：https://github.com/PaddlePaddle/PaddleX/blob/95c53dec89ab0f3769330fa445c6d9213986ca5f/paddlex/cv/models/base.py#L352
model.analyze_sensitivity(
    dataset=eval_dataset,
    batch_size=1,
    save_dir='output/yolov3_darknet53/prune')

# Step 2/3: 根据选择的FLOPs减小比例对模型进行剪裁
# API说明：https://github.com/PaddlePaddle/PaddleX/blob/95c53dec89ab0f3769330fa445c6d9213986ca5f/paddlex/cv/models/base.py#L394
model.prune(pruned_flops=.2)

# Step 3/3: Retrain the model
model.train(
    num_epochs=270,
    train_dataset=train_dataset,
    train_batch_size=8,
    eval_dataset=eval_dataset,
    learning_rate=0.001 / 8,
    warmup_steps=1000,
    warmup_start_lr=0.0,
    save_interval_epochs=5,
    lr_decay_epochs=[216, 243],
    save_dir='output/yolov3_darknet53/prune')
