# modified from github.com/SaoYan/DnCNN-PyTorch/blob/master/train.py
import torch
import torch.nn as nn
from torch.autograd import Variable
from torch.nn import functional as f
import os
import argparse
from model import DnCNN
from dataset import *
import glob
import torch.optim as optim
import uproot
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

# parse arguments
parser = argparse.ArgumentParser(description="DnCNN")
parser.add_argument("training_path", nargs="?", type=str, default="./data/training", help='path of .root data set to be used for training')
parser.add_argument("validation_path", nargs="?", type=str, default="./data/validation", help='path of .root data set to be used for validation')
parser.add_argument("--num_of_layers", type=int, default=9, help="Number of total layers")
parser.add_argument("--sigma", type=float, default=25, help='noise level; ignored when mode=B')

opt = parser.parse_args()

def init_weights(m):
    if type(m) == nn.Linear:
        torch.nn.init.xavier_uniform(m.weight)
        m.bias.data.fill_(0.01)

def patch_based_loss(output, target, patch_size):
    # split output and target images into patches
    output_patches = output.unfold(0, patch_size, patch_size).unfold(1, patch_size, patch_size)
    target_patches = target.unfold(0, patch_size, patch_size).unfold(1, patch_size, patch_size)
    losses = np.zeros(list(output_patches.size())[1])
    # calculate loss for each patch of the image
    for i in range(list(output_patches.size())[1]):
        losses[i] = f.l1_loss(output_patches[0][i], target_patches[0][i])
    return np.max(losses);

if __name__=="__main__":
    net = DnCNN(channels=1, num_of_layers=opt.num_of_layers)
    net.apply(init_weights)
    #TODO implement use of gpu
    
    device_ids = [0]
    m = nn.DataParallel(net, device_ids=device_ids)
    optimizer = optim.Adam(m.parameters(), lr = 0.001)
    # get names of files for training and validation
    training_files = glob.glob(os.path.join(opt.training_path, '*.root'))
    validation_files = glob.glob(os.path.join(opt.validation_path, '*root'))
    print("training files found:")
    print(training_files)
    for training_file in training_files:
        branch = get_all_histograms(training_file)
        for i in range(1):
            m.train()
            m.zero_grad()
            optimizer.zero_grad()
            data = get_bin_weights(branch, i).copy()
            noisy = add_noise(data, opt.sigma).copy()
            data = torch.from_numpy(data)
            noisy = torch.from_numpy(noisy)
            output = m(noisy)
            loss = patch_based_loss(output, data, 10)
            loss.backward()
            optimizer.step()
            m.eval()
    #validation
    for i in range(len(validation_files)):
        data = torch.from_numpy(dataset.get_bin_weights(validation_files[i], 0))
        noisy = torch.from_numpy(dataset.add_noise(data, opt.sigma))
        output = m(noisy)
        
