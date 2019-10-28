import numpy as np
import torch
import torchvision
from time import time
from torchvision import datasets, transforms
from torch import nn, optim
import torch.nn.functional as F


class AllConvNet(nn.Module):
    """https://github.com/StefOe/all-conv-pytorch/blob/master/cifar10.ipynb"""
    def __init__(self, n_classes=10, **kwargs):
        super(AllConvNet, self).__init__()
        self.conv1 = nn.Conv2d(3, 96, 3, padding=1)
        self.conv2 = nn.Conv2d(96, 96, 3, padding=1)
        self.conv3 = nn.Conv2d(96, 96, 3, padding=1, stride=2)
        self.conv4 = nn.Conv2d(96, 192, 3, padding=1)
        self.conv5 = nn.Conv2d(192, 192, 3, padding=1)
        self.conv6 = nn.Conv2d(192, 192, 3, padding=1, stride=2)
        self.conv7 = nn.Conv2d(192, 192, 3, padding=1)
        self.conv8 = nn.Conv2d(192, 192, 1)
        self.class_conv = nn.Conv2d(192, n_classes, 1)

    def forward(self, x):
        x_drop = F.dropout(x, .2)                         # (3,32,32) -> (3,32,32)
        conv1_out = F.relu(self.conv1(x_drop))            # (3,32,32) -> (96,32,32)
        conv2_out = F.relu(self.conv2(conv1_out))         # (96,32,32) -> (96,32,32)
        conv3_out = F.relu(self.conv3(conv2_out))         # (96,32,32) -> (96,16,16)
        conv3_out_drop = F.dropout(conv3_out, .5)         # (96,16,16) -> (96,16,16)
        conv4_out = F.relu(self.conv4(conv3_out_drop))    # (96,16,16) -> (192,16,16)
        conv5_out = F.relu(self.conv5(conv4_out))         # (192,16,16) -> (192,16,16) 
        conv6_out = F.relu(self.conv6(conv5_out))         # (192,16,16) -> (192,8,8) 
        conv6_out_drop = F.dropout(conv6_out, .5)         # (192,8,8) -> (192,8,8)
        conv7_out = F.relu(self.conv7(conv6_out_drop))    # (192,8,8) -> (192,8,8)
        conv8_out = F.relu(self.conv8(conv7_out))         # (192,8,8) -> (192,8,8)
        class_out = F.relu(self.class_conv(conv8_out))    # (192,8,8) -> (10,8,8)
        pool_out = F.adaptive_avg_pool2d(class_out, 1)    # (10,8,8) -> (10,1,1)
        pool_out = pool_out.squeeze_(-1)
        pool_out = pool_out.squeeze_(-1)
        return pool_out

    @staticmethod
    def transform():
        return transforms.Compose([transforms.Resize( (32,32) ),
                                   transforms.ToTensor(),       
                                   transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))])                             
    def loss(self, x):
        return x


class StochasticKeyNet(AllConvNet):
    def __init__(self, keys=None):
        super(StochasticKeyNet, self).__init__()
        self.conv1 = keynet.layers.KeyedConv2d(3, 96, kernel_size=3, stride=1)  # assumed padding=1
        self.conv2 = keynet.layers.KeyedConv2d(96, 96, kernel_size=3, stride=1)  # assumed padding=1
        self.conv3 = keynet.layers.KeyedConv2d(96, 96, kernel_size=3, stride=2)  # assumed padding=1
        self.conv4 = keynet.layers.KeyedConv2d(96, 192, kernel_size=3, stride=1)  # assumed padding=1
        self.conv5 = keynet.layers.KeyedConv2d(192, 192, kernel_size=3, stride=1)  # assumed padding=1
        self.conv6 = keynet.layers.KeyedConv2d(192, 192, kernel_size=3, stride=2)  # assumed padding=1
        self.conv7 = keynet.layers.KeyedConv2d(192, 192, kernel_size=3, stride=1)  # assumed padding=1
        self.conv8 = keynet.layers.KeyedConv2d(192, 192, kernel_size=3, stride=1)  # assumed padding=1
        self.conv9 = keynet.layers.KeyedConv2d(192, 10, kernel_size=3, stride=1)  # assumed padding=1
        self.pool10 = keynet.layers.KeyedAvgpool2d(10, 10, kernel_size=8, stride=8)  # FIXME

        # Layer input shapes:  conv1(x1), conv8(x8)
        self.shape = {'x0':(3,32,32),   # image input
                      'x1':(3,32,32),  
                      'x2':(96,32,32),  
                      'x3':(96,32,32), 
                      'x4':(96,16,16), 
                      'x5':(192,16,16),   
                      'x6':(192,16,16),   
                      'x7':(192,8,8),  
                      'x8':(192,8,8),  
                      'x9':(192,8,8),   
                      'x10':(10,8,8)}   

        permutation_keys = {'A1':sparse_permutation_matrix(np.prod(self.shape['x1'])+1),
                            'A2':sparse_permutation_matrix(np.prod(self.shape['x2'])+1),
                            'A3':sparse_permutation_matrix(np.prod(self.shape['x3'])+1),
                            'A4':sparse_permutation_matrix(np.prod(self.shape['x4'])+1),
                            'A5':sparse_permutation_matrix(np.prod(self.shape['x5'])+1),
                            'A6':sparse_permutation_matrix(np.prod(self.shape['x6'])+1),
                            'A7':sparse_permutation_matrix(np.prod(self.shape['x7'])+1),
                            'A8':sparse_permutation_matrix(np.prod(self.shape['x7'])+1),
                            'A9':sparse_permutation_matrix(np.prod(self.shape['x7'])+1),
                            'A10':sparse_permutation_matrix(np.prod(self.shape['x7'])+1)}
        
        permutation_keys.update({'A1inv':permutation_keys['A1'].transpose(),
                                 'A2inv':permutation_keys['A2'].transpose(),
                                 'A3inv':permutation_keys['A3'].transpose(),
                                 'A4inv':permutation_keys['A4'].transpose(),
                                 'A5inv':permutation_keys['A5'].transpose(),
                                 'A6inv':permutation_keys['A6'].transpose(),
                                 'A7inv':permutation_keys['A7'].transpose(),
                                 'A8inv':permutation_keys['A8'].transpose(),
                                 'A9inv':permutation_keys['A9'].transpose(),
                                 'A10inv':permutation_keys['A10'].transpose()})

        diagonal_keys = {'A1':sparse_uniform_random_diagonal_matrix(np.prod(self.shape['x1'])+1),
                         'A2':sparse_uniform_random_diagonal_matrix(np.prod(self.shape['x2'])+1),
                         'A3':sparse_uniform_random_diagonal_matrix(np.prod(self.shape['x3'])+1),
                         'A4':sparse_uniform_random_diagonal_matrix(np.prod(self.shape['x4'])+1),
                         'A5':sparse_uniform_random_diagonal_matrix(np.prod(self.shape['x5'])+1),
                         'A6':sparse_uniform_random_diagonal_matrix(np.prod(self.shape['x6'])+1),
                         'A7':sparse_uniform_random_diagonal_matrix(np.prod(self.shape['x7'])+1),
                         'A8':sparse_uniform_random_diagonal_matrix(np.prod(self.shape['x8'])+1),
                         'A9':sparse_uniform_random_diagonal_matrix(np.prod(self.shape['x9'])+1),
                         'A10':sparse_uniform_random_diagonal_matrix(np.prod(self.shape['x10'])+1)}
        
        diagonal_keys.update({'A1inv':sparse_inverse_diagonal_matrix(diagonal_keys['A1']),
                              'A2inv':sparse_inverse_diagonal_matrix(diagonal_keys['A2']),
                              'A3inv':sparse_inverse_diagonal_matrix(diagonal_keys['A3']),
                              'A4inv':sparse_inverse_diagonal_matrix(diagonal_keys['A4']),
                              'A5inv':sparse_inverse_diagonal_matrix(diagonal_keys['A5']),
                              'A6inv':sparse_inverse_diagonal_matrix(diagonal_keys['A6']),
                              'A7inv':sparse_inverse_diagonal_matrix(diagonal_keys['A7']),
                              'A8inv':sparse_inverse_diagonal_matrix(diagonal_keys['A8']),
                              'A9inv':sparse_inverse_diagonal_matrix(diagonal_keys['A9']),
                              'A10inv':sparse_inverse_diagonal_matrix(diagonal_keys['A10'])})

        keys = {k:diagonal_keys[k].dot(permutation_keys[k]) if 'inv' not in k else permutation_keys[k].dot(diagonal_keys[k]) for k in permutation_keys.keys()}
        keys.update( {'A0inv':None} )
        self.keys = keys

        
    def load_state_dict_keyed(self, d_state, A0inv):        
        self.conv1.key(np.array(d_state['conv1.weight']), np.array(d_state['conv1.bias']), self.keys['A1'], A0inv, self.shape['x1'])
        self.conv2.key(np.array(d_state['conv2.weight']), np.array(d_state['conv2.bias']), self.keys['A2'], A1inv, self.shape['x2'])
        self.conv3.key(np.array(d_state['conv3.weight']), np.array(d_state['conv3.bias']), self.keys['A3'], A2inv, self.shape['x3'])
        self.conv4.key(np.array(d_state['conv4.weight']), np.array(d_state['conv4.bias']), self.keys['A4'], A3inv, self.shape['x4'])
        self.conv5.key(np.array(d_state['conv5.weight']), np.array(d_state['conv5.bias']), self.keys['A5'], A4inv, self.shape['x5'])
        self.conv6.key(np.array(d_state['conv6.weight']), np.array(d_state['conv6.bias']), self.keys['A6'], A5inv, self.shape['x6'])
        self.conv7.key(np.array(d_state['conv7.weight']), np.array(d_state['conv7.bias']), self.keys['A7'], A6inv, self.shape['x7'])
        self.conv8.key(np.array(d_state['conv8.weight']), np.array(d_state['conv8.bias']), self.keys['A8'], A7inv, self.shape['x8'])
        self.conv9.key(np.array(d_state['conv9.weight']), np.array(d_state['conv9.bias']), self.keys['A9'], A8inv, self.shape['x9'])
        self.pool10.key(self.keys['A10'], self.keys['A10inv'], self.shape['x10'])


    def forward(self, A0x0_affine):
        x_drop = A0x0_affine                              # (3,32,32) -> (3,32,32)
        conv1_out = F.relu(self.conv1(x_drop))            # (3,32,32) -> (96,32,32)
        conv2_out = F.relu(self.conv2(conv1_out))         # (96,32,32) -> (96,32,32)
        conv3_out = F.relu(self.conv3(conv2_out))         # (96,32,32) -> (96,16,16)
        conv3_out_drop = conv3_out                        # (96,16,16) -> (96,16,16)
        conv4_out = F.relu(self.conv4(conv3_out_drop))    # (96,16,16) -> (192,16,16)
        conv5_out = F.relu(self.conv5(conv4_out))         # (192,16,16) -> (192,16,16) 
        conv6_out = F.relu(self.conv6(conv5_out))         # (192,16,16) -> (192,8,8) 
        conv6_out_drop = conv6_out                        # (192,8,8) -> (192,8,8)
        conv7_out = F.relu(self.conv7(conv6_out_drop))    # (192,8,8) -> (192,8,8)
        conv8_out = F.relu(self.conv8(conv7_out))         # (192,8,8) -> (192,8,8)
        conv9_out = F.relu(self.conv9(conv8_out))         # (192,8,8) -> (10,8,8)
        pool10_out = self.pool10(conv9_out, 1)            # (10,8,8) -> (10,1,1)
        pool10_out.squeeze_(-1)  # FIXME
        pool10_out.squeeze_(-1)
        return pool_out

    def encrypt(self, A0, x):        
        return torch.tensor(A0.dot(torch_affine_augmentation_tensor(x))) if A0 is not None else x

    def decrypt(self, x):
        if self.keys['A10inv'] is not None and self.keys['A10'] is not None:
            return torch_affine_deaugmentation_tensor(torch.tensor(self.keys['A10inv'].dot(x)))
        else:
            return torch_affine_deaugmentation_tensor(x)

    def loss(self, x):
        return self.decrypt(x)




def validate(net, cifardir='/proj/enigma', secretkey=None):
    testset = torchvision.datasets.CIFAR10(root=cifardir, train=False, download=True, transform=net.transform())
    testloader = torch.utils.data.DataLoader(testset, batch_size=4, shuffle=False, num_workers=2)
    net.eval()

    (total, correct) = (0,0)
    for images,labels in testloader:
        for i in range(len(labels)):
            with torch.no_grad():
                output = net.loss(net(images if secretkey is None else net.encrypt(secretkey,images)))
            _, pred = torch.max(output, 1)
            #pred = output.argmax(dim=1, keepdim=True) 
            total += labels.size(0)
            correct += (pred == labels).sum().item()

    print("Mean classification accuracy = %f" % (correct/total))


def train(net, modelfile, cifardir='/proj/enigma', epochs=40, lr=0.001):
    trainset = torchvision.datasets.CIFAR10(root=cifardir, train=True, download=True, transform=net.transform())
    trainloader = torch.utils.data.DataLoader(trainset, batch_size=4, shuffle=True, num_workers=2)
    classes = ('plane', 'car', 'bird', 'cat', 'deer', 'dog', 'frog', 'horse', 'ship', 'truck')
    
    with torch.enable_grad():
        net.train()
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.SGD(net.parameters(), lr=lr, momentum=0.9)
        #scheduler = optim.lr_scheduler.MultiStepLR(optimizer, milestones=[200, 250, 300], gamma=0.1)  # FIXME
        time0 = time()

        for e in range(epochs):
            running_loss = 0
            for images, labels in trainloader:
                optimizer.zero_grad()            
                output = net(images)
                loss = criterion(output, labels)                
                loss.backward()
                optimizer.step()        
                running_loss += loss.item()
            else:
                print("Epoch {} - Training loss: {}".format(e, running_loss/len(trainloader)))

            #scheduler.step()
            print("Training Time (in minutes) =",(time()-time0)/60)

    torch.save(net.state_dict(), modelfile)
    return net


def allconv():
    net = train(AllConvNet(), modelfile='/proj/enigma/jebyrne/cifar_allconv.pth', lr=0.001, epochs=40)
    validate(net)

