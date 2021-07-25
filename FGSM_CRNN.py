import torch
import torchvision
from dataset import *
from utils import *
from PIL import Image
import models.crnn as crnn
import numpy as np 
import torch.optim as optim
from  torchvision import utils as vutils
# import matplotlib.pyplot as plt
# from Chinese_alphabet import alphabet
use_cuda=True
model_path = './data/crnn.pth'  # 英文模型权重路径
# model_path = './data/netCRNN.pth'  # 中文模型权重路径
img_path = './data/demo.png'  # 测试图片路径
alphabet = '0123456789abcdefghijklmnopqrstuvwxyz'

epsilon = [0, 0.2, 0.5, 1, 5]# FGSM攻击参数
# epsilon = 5

# Define what device we are using
print("CUDA Available: ",torch.cuda.is_available())
device = torch.device("cuda" if (use_cuda and torch.cuda.is_available()) else "cpu")

model = crnn.CRNN(32, 1, len(alphabet) + 1, 256).to(device)  # 创建模型

# Load pre-train model
print('loading pretrained model from %s' % model_path)
model.load_state_dict(torch.load(model_path))

# 创建转换器，测试阶段用于将ctc生成的路径转换成最终序列，使用英文字典时忽略大小写
converter = strLabelConverter(alphabet, ignore_case=False)

# 图像大小转换器
transformer = resizeNormalize((100, 32))

# FGSM attack 
def fgsm_attack(image, epsilon, data_grad):
    # Collect the element-wise sign of the data gradient
    sign_data_grad = data_grad.sign()
    # Create the perturbed image by adjusting each pixel of the input image
    image = image.squeeze(1)
    
    sign_data_grad = sign_data_grad.resize_([1,32,100])  
    sign_data_grad = sign_data_grad.sign() # 此句加与不加输出值不同，但不影响程序
    perturbed_image = image + epsilon*sign_data_grad
    
    # Adding clipping to maintain [0,1] range
    perturbed_image = torch.clamp(perturbed_image, 0, 1)

    # Return the perturbed image   
    perturbed_image = perturbed_image.unsqueeze(1)
    # save perturbed_image
    vutils.save_image(perturbed_image, './data/adv_fgsm.png', normalize=True)
    # plt.imshow(perturbed_image, cmap="gray")
    # plt.savefig('./data/adv_fgsm.jpg')
    # plt.close()
    return perturbed_image

# 读取并转换图像大小为100 x 32 w x h
image = Image.open(img_path).convert('L')  #参数'L'表示将图像转为灰度图
image = transformer(image) # (1, 32, 100)
image = image.view(1, *image.size())  # (b, c, h, w) (1, 1, 32, 100)

model.eval()

criterion = torch.nn.CTCLoss()

def test( model, device, epsilon ):

    # Send the data to the device
    # target = [24, 11, 418, 323, 446, 2, 350, 335, 291, 109] # 不需要输入图片的label，label由alphabet提供
    data = image
    data = data.to(device)

    # Set requires_grad attribute of tensor. Important for Attack
    # data.requires_grad = True # data不需要获得梯度，梯度由model的输出preds提供

    # Forward pass the data through the model
    preds = model(data)
    preds = Variable(preds, requires_grad=True)
    
    # ctcloss的参数
    batch_size = data.size(0)
    target, length = converter.encode(alphabet)  # encode函数，提供target和target的length

    preds_size = torch.IntTensor([preds.size(0)] * batch_size)

    # Calculate the loss
    loss = criterion(preds, target, preds_size, length)

    # Zero all existing gradients
    model.zero_grad()

    # Calculate gradients of model in backward pass
    loss.backward()

    # Collect datagrad
    data_grad = preds.grad

    # Call FGSM Attack
    perturbed_data = fgsm_attack(data, epsilon, data_grad)

    # Re-classify the perturbed image
    output = model(perturbed_data)
    _, output = output.max(2)  # 取可能性最大的indecis size (26, 1)
    output = output.transpose(1, 0).contiguous().view(-1)  # 转成以为索引列表
    # 转成字符序列
    output_size = torch.IntTensor([output.size(0)])
    raw_output = converter.decode(output.data, output_size.data, raw=True)
    sim_output = converter.decode(output.data, output_size.data, raw=False)
    
    return raw_output, sim_output

# raw_output, sim_output = test(model, device, epsilon)
# print('%-20s => %-20s' % (raw_output, sim_output))

# Run test for each epsilon
raw_output = []
sim_output = []
for eps in epsilon:
    raw_output, sim_output = test(model, device, eps)
    print("Epsilon: {}\t {} => {}".format(eps, raw_output, sim_output))