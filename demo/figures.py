import numpy as np
from numpy.linalg import multi_dot 
import keynet.util
import vipy.image
import vipy.visualize
import copy
import torch
import torchvision
from torch import nn
from torchvision import datasets, transforms
from vipy.util import Stopwatch, tempdir
from keynet.sparse import sparse_toeplitz_conv2d
from keynet.sparse import sparse_toeplitz_avgpool2d
from keynet.util import torch_avgpool2d_in_scipy, torch_conv2d_in_scipy
import keynet.util
import keynet.blockpermute
import keynet.mnist
import keynet.cifar10
import keynet.torch
import keynet.fiberbundle
from keynet.mnist import LeNet, LeNet_AvgPool
from keynet.cifar10 import AllConvNet
import keynet.system
import keynet.dense
import keynet.globals
import keynet.vgg


def example_2x2():
    """Reproduce example 2x2 image figure in paper"""
    np.random.seed(0)

    img = np.array([[11,12],[21,22]]).astype(np.float32)
    x = img.flatten().reshape(4,1)
    D1 = keynet.dense.uniform_random_diagonal_matrix(4)
    P1 = keynet.dense.random_doubly_stochastic_matrix(4,2)
    A1 = np.dot(D1,P1)
    A1inv = np.linalg.inv(A1)

    P2 = keynet.dense.random_permutation_matrix(4)
    D2 = keynet.dense.uniform_random_diagonal_matrix(4)
    A2 = np.dot(D2,P2)
    A2inv = np.linalg.inv(A2)

    W1 = np.array([[-1,1,0,0],[0,-1,0,0],[0,0,-1,1],[0,0,0,-1]]).astype(np.float32)
    W1hat = multi_dot( (A2,W1,A1inv) )

    print('img')
    print(img)

    print('x')
    print(x)

    print('D1')
    print(D1)
    print('P1')
    print(P1)
    print('A1')
    print(A1)

    print('W1')
    print(W1)
    print('W1hat')
    print(W1hat)

    print('A1inv*A1')
    print(np.dot(A1inv, A1))

    print('A2')
    print(A2)

    x1h = multi_dot( (W1hat, A1, x) )

    x2h = copy.deepcopy(x1h)
    x2h[x2h<=0] = 0  # ReLU

    x1 = multi_dot( (W1, x) )
    x2 = copy.deepcopy(x1)
    x2[x2<=0] = 0  # ReLU

    print('A1*x, x1, x1h, x2, x2h, A2inv * x2h')
    print(multi_dot( (A1, x) ))
    print(x1)
    print(x1h)

    print(x2)
    print(x2h)
    print(multi_dot( (A2inv, x2h) ))

    
def optical_transformation_montage(imgfile=None):
    """Reproduce figure in paper"""

    (m,n) = (256,256)
    img = vipy.image.Image(imgfile if imgfile is not None else 'owl.jpg').resize(256,256).rgb().numpy()

    D = [np.maximum(1E-6, 1.0 + (s*np.random.rand( m,n,3 )-(s/2.0))) for s in [0.1, 1.0, 10000.0]]
    B = [255*np.maximum(1E-6, s*np.random.rand( m,n,3 )) for s in [0.1, 1.0, 10000.0]]
    P = [img,  # no permutation
         keynet.blockpermute.hierarchical_block_permute(img, (2,2), permute_at_level=range(6,8), min_blockshape=1),
         keynet.blockpermute.hierarchical_block_permute(img, (2,2), permute_at_level=range(5,6), min_blockshape=1),
         keynet.blockpermute.hierarchical_block_permute(img, (2,2), permute_at_level=range(4,5), min_blockshape=1),
         keynet.blockpermute.hierarchical_block_permute(img, (2,2), permute_at_level=range(3,5), min_blockshape=1),
         keynet.blockpermute.hierarchical_block_permute(img, (2,2), permute_at_level=range(2,6), min_blockshape=1),
         keynet.blockpermute.hierarchical_block_permute(img, (2,2), permute_at_level=range(0,8), min_blockshape=1)]
    
    imlist = []
    for (d,b) in zip(D,B):
        for p in P:
            img_permuted = p
            img_scaled = np.multiply(d, img_permuted) + b
            img_scaled = np.uint8(255*((img_scaled-np.min(img_scaled))/ (np.max(img_scaled)-np.min(img_scaled))))
            imlist.append(vipy.image.Image(array=img_scaled, colorspace='rgb'))

    img_montage = vipy.visualize.montage(imlist, 256,256, gridrows=3, gridcols=7)

    print(img_montage.saveastmp())
    return img_montage

    
def train_mnist_lenet():
    """Reproduce results in figure 6, 'raw' column"""
    net = keynet.mnist.train(LeNet(), modelfile='../models/mnist_lenet.pth', lr=0.003, epochs=20)
    keynet.mnist.validate(net)


def train_mnist_lenet_avgpool():
    """Reproduce results in figure 6, 'raw' column"""
    net = keynet.mnist.train(LeNet_AvgPool(), modelfile='../models/mnist_lenet_avgpool.pth', lr=0.003, epochs=40)
    keynet.mnist.validate(net)

    
def train_mnist_lenet_avgpool_fiberbundle(do_mean_estimation=True, mnistdir=tempdir()):
    """Reproduce results in figure 6, 'sim' column"""
    # Mean
    if do_mean_estimation:
        transform = transforms.Compose([transforms.Lambda(lambda img: keynet.fiberbundle.transform(img.convert('RGB'), (28,28))),
                                        transforms.Grayscale(),
                                        transforms.Resize( (28,28) ),
                                        transforms.ToTensor()])
    
        trainset = torchvision.datasets.MNIST(root=tempdir(), train=True, download=True, transform=transform)
        trainloader = torch.utils.data.DataLoader(trainset, batch_size=1, shuffle=True, num_workers=32)
        imglist = []
        for (k, (images,labels)) in enumerate(trainloader):
            imglist.append(images)
            if k > 1024:
                break
        mu = np.mean(np.array(images).flatten())
        std = np.std(np.array(images).flatten())
        print(mu,std)
    else:
        (mu, std) = (0.46616146, 0.06223659)

    # Load full transformed dataset in memory (parallelized)
    transform = transforms.Compose([transforms.Lambda(lambda img: keynet.fiberbundle.transform(img.convert('RGB'), (28,28))),
                                    transforms.Grayscale(),
                                    transforms.Resize( (28,28) ),
                                    transforms.ToTensor(),
                                    transforms.Normalize((mu,), (std,))])

    trainset = torchvision.datasets.MNIST(root=mnistdir, train=True, download=True, transform=transform)
    trainloader = torch.utils.data.DataLoader(trainset, batch_size=32, shuffle=True, num_workers=32)
    trainpreload = [(x,y) for (x,y) in trainloader]
    testset = torchvision.datasets.MNIST(root=mnistdir, train=False, download=True, transform=transform)
    testloader = torch.utils.data.DataLoader(testset, batch_size=32, shuffle=False, num_workers=32)
    testpreload = [(x,y) for (x,y) in testloader]

    # Validate (lenet)
    net1 = keynet.mnist.LeNet_AvgPool()
    net1.load_state_dict(torch.load('../models/mnist_lenet_avgpool.pth'))
    keynet.cifar10.validate(net1, testloader=testpreload)

    # Re-train and Re-validate (lenet)
    net2 = keynet.mnist.LeNet_AvgPool()
    keynet.cifar10.train(net2, modelfile='../models/mnist_lenet_avgpool_fiberbundle.pth', lr=0.004, epochs=40, trainloader=trainpreload)
    net3 = keynet.mnist.LeNet_AvgPool()
    net3.load_state_dict(torch.load('../models/mnist_lenet_avgpool_fiberbundle.pth'))
    keynet.cifar10.validate(net3, testloader=testpreload)


def train_cifar10_allconv():
    """Reproduce results in figure 6"""
    keynet.cifar10.train(keynet.cifar10.AllConvNet(), modelfile='../models/cifar10_allconv.pth', lr=0.01, epochs=350)
    testmodel = keynet.cifar10.AllConvNet()
    testmodel.load_state_dict(torch.load('../models/cifar10_allconv.pth'))
    keynet.cifar10.validate(testmodel)

    
def train_cifar10_allconv_fiberbundle(do_mean_estimation=True, cifardir='/proj/enigma'):
    """Reproduce results in figure 6, 'sim' column"""
    if do_mean_estimation:
        transform = transforms.Compose([transforms.Lambda(lambda img: keynet.fiberbundle.transform(img, (32,32))),
                                        transforms.ToTensor()])
    
        trainset = torchvision.datasets.CIFAR10(root='/proj/enigma', train=True, download=True, transform=transform)
        trainloader = torch.utils.data.DataLoader(trainset, batch_size=1024, shuffle=True, num_workers=32)
        for (images,labels) in trainloader:
            mu = np.mean(np.array(images), axis=(0,2,3))
            std = np.std(np.array(images), axis=(0,2,3))
            break
        print(mu,std)
    else:
        (mu, std) = ([0.5864967,  0.58052236, 0.48031753], [0.08658934, 0.09825305, 0.04734877])

    # Load full transformed dataset in memory (parallelized)
    train_transform = transforms.Compose([transforms.Lambda(lambda img: keynet.fiberbundle.transform(img, (32,32))),
                                          transforms.RandomCrop(32, padding=4),
                                          transforms.RandomHorizontalFlip(),
                                          transforms.ToTensor(),
                                          transforms.Normalize(mu, std)])
    test_transform = transforms.Compose([transforms.Lambda(lambda img: keynet.fiberbundle.transform(img, (32,32))),
                                         transforms.ToTensor(),
                                         transforms.Normalize(mu, std)])
                                        
    trainset = torchvision.datasets.CIFAR10(root=cifardir, train=True, download=True, transform=train_transform)
    trainloader = torch.utils.data.DataLoader(trainset, batch_size=32, shuffle=True, num_workers=32)
    trainpreload = [(x,y) for (x,y) in trainloader]
    testset = torchvision.datasets.CIFAR10(root=cifardir, train=False, download=True, transform=test_transform)
    testloader = torch.utils.data.DataLoader(testset, batch_size=32, shuffle=False, num_workers=32)
    testpreload = [(x,y) for (x,y) in testloader]

    # Validate (allconv)
    net1 = keynet.cifar10.AllConvNet(3)
    net1.load_state_dict(torch.load('../models/cifar10_allconv.pth'))
    keynet.cifar10.validate(net1, testloader=testpreload)

    # Re-train and Re-validate (lenet)
    net2 = keynet.cifar10.AllConvNet(3)
    keynet.cifar10.train(net2, modelfile='../models/cifar10_allconv_fiberbundle.pth', lr=0.01, epochs=350, trainloader=trainpreload)
    net3 = AllConvNet(3)
    net3.load_state_dict(torch.load('../models/cifar10_allconv_fiberbundle.pth'))
    keynet.cifar10.validate(net3, testloader=testpreload)


def print_parameters():
    keynet.globals.verbose(False)

    inshape = (1,28,28)
    net = keynet.mnist.LeNet_AvgPool()
    net.load_state_dict(torch.load('../models/mnist_lenet_avgpool.pth'));
    print('[figures.print_parameters]:  lenet parameters=%d' % (keynet.torch.count_parameters(net)))
    
    (sensor, knet) = keynet.system.IdentityKeynet(inshape, net)
    print('[figures.print_parameters]:  IdentityKeynet (lenet) parameters=%d' % (knet.num_parameters()))        

    (sensor, knet) = keynet.system.PermutationKeynet(inshape, net)
    print('[figures.print_parameters]:  PermutationKeynet (lenet) parameters=%d' % (knet.num_parameters()))        

    (sensor, knet) = keynet.system.TiledPermutationKeynet(inshape, net, 2)
    print('[figures.print_parameters]:  TiledPermutationKeynet-2 (lenet) parameters=%d' % (knet.num_parameters()))        

    (sensor, knet) = keynet.system.TiledPermutationKeynet(inshape, net, 4)
    print('[figures.print_parameters]:  TiledPermutationKeynet-4 (lenet) parameters=%d' % (knet.num_parameters()))        

    (sensor, knet) = keynet.system.TiledPermutationKeynet(inshape, net, 8)
    print('[figures.print_parameters]:  TiledPermutationKeynet-8 (lenet) parameters=%d' % (knet.num_parameters()))        

    inshape = (3,32,32)
    net = keynet.cifar10.AllConvNet(batchnorm=False)    
    print('[figures.print_parameters]:  allconvnet parameters=%d' % (keynet.torch.count_parameters(net)))
    
    (sensor, knet) = keynet.system.IdentityKeynet(inshape, net)    
    print('[figures.print_parameters]:  IdentityKeynet (allconvnet) parameters=%d' % (knet.num_parameters()))

    (sensor, knet) = keynet.system.PermutationKeynet(inshape, net)    
    print('[figures.print_parameters]:  PermutationKeynet (allconvnet) parameters=%d' % (knet.num_parameters()))

    for k in [2,4,8,16]:
        (sensor, knet) = keynet.system.TiledPermutationKeynet(inshape, net, k)
        print('[figures.print_parameters]:  TiledPermutationKeynet-%d (allconvnet) parameters=%d' % (k, knet.num_parameters()))        

    for k in [2,4,8,16]:
        (sensor, knet) = keynet.system.TiledOrthogonalKeynet(inshape, net, k)
        print('[figures.print_parameters]:  TiledOrthogonalKeynet-%d (allconvnet) parameters=%d' % (k, knet.num_parameters()))        

    inshape = (3,224,224)
    net = keynet.vgg.VGG16()
    print('[figures.print_parameters]:  vgg-16 parameters=%d' % (keynet.torch.count_parameters(net)))

    (sensor, knet) = keynet.system.IdentityKeynet(inshape, net)    
    print('[figures.print_parameters]:  IdentityKeynet (vgg-16) parameters=%d' % (knet.num_parameters()))

    (sensor, knet) = keynet.system.PermutationKeynet(inshape, net)    
    print('[figures.print_parameters]:  PermutationKeynet (vgg-16) parameters=%d' % (knet.num_parameters()))

    for k in [2,4,8,16,32]:
        (sensor, knet) = keynet.system.TiledPermutationKeynet(inshape, net, k)
        print('[figures.print_parameters]:  TiledPermutationKeynet-%d (vgg-16) parameters=%d' % (k, knet.num_parameters()))        

    for k in [2,4,8,16,32]:
        (sensor, knet) = keynet.system.TiledOrthogonalKeynet(inshape, net, k)
        print('[figures.print_parameters]:  TiledOrthogonalKeynet-%d (vgg-16) parameters=%d' % (k, knet.num_parameters()))        


if __name__ == '__main__':
    print_parameters()
