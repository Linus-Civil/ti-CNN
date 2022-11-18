import taichi as ti
# 注意单浮点精度问题

ti.init(arch=ti.gpu,device_memory_GB=4.0,default_fp=ti.f64)

# define of convolution layer
@ti.data_oriented
class convolution_layer:
    def __init__(self,width,height,mapsize,inchannels,outchannels,isfullconnect=True):
        self.inputWidth = int(width)                  #int
        self.inputHeight = int(height)                #int
        self.mapSize = mapsize                   #size of convolution kernel,int
        self.inChannels = inchannels             #number of input images, int
        self.outChannels = outchannels           #number of output images, int
        self.isFullConnect = isfullconnect       # default value = true

        # valid mode
        self.outW = int(self.inputWidth - self.mapSize+1)
        self.outH = int(self.inputHeight - self.mapSize + 1)

        self.mapData = ti.field(dtype=ti.f64,shape=(inchannels,outchannels,mapsize,mapsize)) 
        self.biasData = ti.field(dtype=ti.f64,shape=(outchannels,)) # bias

        self.v = ti.field(dtype=ti.f64,shape=(outchannels,self.outH,self.outW)) 
        self.y = ti.field(dtype=ti.f64,shape=(outchannels,self.outH,self.outW)) 
        self.d = ti.field(dtype=ti.f64,shape=(outchannels,self.outH,self.outW)) 

        self.coor = ti.field(dtype=ti.f64,shape=(self.inputHeight,self.inputWidth))
        self.flipmap = ti.field(dtype=ti.f64,shape=(self.mapSize,self.mapSize))
        self.fill_d = ti.field(dtype=ti.f64,shape=(self.outH+2*self.mapSize-2,self.outW+2*self.mapSize-2))
        self.mat_field = ti.Matrix.field(self.mapSize,self.mapSize,ti.f64,shape=(3,))

    @ti.kernel
    def initialize(self):
        for i,j,r,c in ti.ndrange(self.inChannels,self.outChannels,self.mapSize,self.mapSize):
            randnum = (ti.random()-0.5)*2 # -1~1
            self.mapData[i,j,r,c] = randnum*ti.sqrt(6.0/(self.mapSize*self.mapSize*(self.inChannels+self.outChannels)))

        self.biasData.fill(0.)
        self.v.fill(0.)
        self.y.fill(0.)
        self.d.fill(0.)

        mid_ind = int(self.mapSize/2)
        for x,y in ti.static(ti.ndrange(self.mapSize,self.mapSize)):
            if x+y == mid_ind*2:
                self.mat_field[0][x,y] = 1.0  #reverse matrix ; 1-orig; 2-flip

#池化层
@ti.data_oriented
class polling_layer:
    def __init__(self,width,height,mapsize,inchannels,outchannels,pooltype):
        self.inputWidth = int(width)
        self.inputHeight = int(height)
        self.mapSize = mapsize  #size of convolution kernel
        self.inChannels = inchannels #number of input images
        self.outChannels = outchannels #number of output images
        self.poolType = pooltype #1-max,0-average

        self.outW = int(self.inputWidth/self.mapSize)
        self.outH = int(self.inputHeight/self.mapSize)

        self.biasData = ti.field(dtype=ti.f64, shape=(outchannels,))  # bias
        self.y = ti.field(dtype=ti.f64,shape=(outchannels,self.outH,self.outW)) 
        self.d = ti.field(dtype=ti.f64,shape=(outchannels,self.outH,self.outW)) 
        self.max_position = ti.field(dtype=ti.i32,shape=(outchannels,self.outH,self.outW))

        self.matC3e = ti.field(dtype=ti.f64,shape=(self.inputHeight,self.inputWidth))


    @ti.kernel
    def initialize(self):
        self.biasData.fill(0.)
        self.y.fill(0.)
        self.d.fill(0.)
        self.max_position.fill(0)

#输出层
@ti.data_oriented
class out_layer:
    def __init__(self,inputNum,outputNum,isfullconnect=True):
        inputNum = int(inputNum)
        outputNum = int(outputNum)
        self.inputNum = inputNum
        self.outputNum = outputNum
        self.isFullConnect = isfullconnect

        self.wData = ti.field(dtype=ti.f64,shape=(outputNum,inputNum))
        self.biasData = ti.field(dtype=ti.f64, shape=(outputNum,))

        self.v = ti.field(dtype=ti.f64, shape=(outputNum,))
        self.y = ti.field(dtype=ti.f64, shape=(outputNum,))
        self.d = ti.field(dtype=ti.f64, shape=(outputNum,))


    @ti.kernel
    def initialize(self):
        self.biasData.fill(0.)
        self.v.fill(0.)
        self.y.fill(0.)
        self.d.fill(0.)
        for i,j in ti.ndrange(self.outputNum,self.inputNum):
            randnum = (ti.random()-0.5)*2
            self.wData[i,j] = randnum*ti.sqrt(6.0/(self.inputNum+self.outputNum))

# cnn of 5 layer
@ti.data_oriented
class cnn_network:
    def __init__(self,init_h,init_w): #28*28
        self.layerNum = 5
        #第一层卷积核尺寸为5，卷积神经元数量为6
        self.CovLayer_1 = convolution_layer(height=init_h,width=init_w,mapsize=5,inchannels=1,outchannels=6)
        self.CovLayer_1.initialize()
        pl1_h = init_h-self.CovLayer_1.mapSize+1 #24
        pl1_w = init_w - self.CovLayer_1.mapSize + 1  # 24

        self.PoolLayer_1 = polling_layer(height=pl1_h,width=pl1_w,mapsize=2,inchannels=self.CovLayer_1.outChannels,outchannels=self.CovLayer_1.outChannels,pooltype=1)
        self.PoolLayer_1.initialize()
        cl2_h = pl1_h/self.PoolLayer_1.mapSize
        cl2_w = pl1_w / self.PoolLayer_1.mapSize #12*12

        self.CovLayer_2 = convolution_layer(height=cl2_h,width=cl2_w,mapsize=5,inchannels=self.PoolLayer_1.outChannels,outchannels=12)
        self.CovLayer_2.initialize()
        pl2_h = cl2_h-self.CovLayer_2.mapSize+1
        pl2_w = cl2_w-self.CovLayer_2.mapSize+1 #8*8

        self.PoolLayer_2 = polling_layer(height=pl2_h,width=pl2_w,mapsize=2,inchannels=self.CovLayer_2.outChannels,outchannels=self.CovLayer_2.outChannels,pooltype=1)
        self.PoolLayer_2.initialize()
        ol_h = pl2_h/self.PoolLayer_2.mapSize
        ol_w = pl2_w/self.PoolLayer_2.mapSize #4*4

        self.OutLayer = out_layer(inputNum=ol_h*ol_w*self.PoolLayer_2.outChannels,outputNum=10)
        self.OutLayer.initialize()
        print(self.OutLayer.inputNum,self.OutLayer.outputNum)

        self.e = ti.field(ti.f64,shape=(self.OutLayer.outputNum,))
        self.e.fill(0.) #训练误差
        self.L = None  #瞬时误差能量

# 训练参数
@ti.data_oriented
class train_opts:
    def __init__(self):
        self.numepochs = None #num of iteration
        self.alpha = None # learning rate

# 卷积
@ti.func
def cov_multiply(i,j,inpudata,mapdata,oh,ow,mapsize):
    s = 0.0
    for x,y in ti.ndrange(mapsize,mapsize):
        s += inpudata[j,oh+x,ow+y]*mapdata[j,i,x,y]
    return s

#Relu
@ti.func
def activation_sigma(inputd,bias):
    temp = inputd+bias
    if temp <= 0:
        temp = 0
    return temp

@ti.kernel
def cov_layer_ff(inputdata:ti.template(),covlayer:ti.template()):
    for i,j in ti.ndrange(covlayer.outChannels,covlayer.inChannels):
        for oh,ow in ti.ndrange(covlayer.outH,covlayer.outW):
            covlayer.v[i,oh,ow] += cov_multiply(i,j,inputdata,covlayer.mapData,oh,ow,covlayer.mapSize)

    for i,r,c in ti.ndrange(covlayer.outChannels,covlayer.outH,covlayer.outW):
        covlayer.y[i,r,c] = activation_sigma(covlayer.v[i,r,c],covlayer.biasData[i])

@ti.kernel
def pool_layer_ff(inputdata:ti.template(),poolayer:ti.template()):
    mpszie = poolayer.mapSize
    num,rows,cols = inputdata.shape
    for i,r,c in ti.ndrange(poolayer.outChannels,poolayer.outH,poolayer.outW):
        max = -99999999.0
        max_index = 0
        for m,n in ti.ndrange((r*mpszie,r*mpszie+mpszie),(c*mpszie,c*mpszie+mpszie)):
            if inputdata[i,m,n] > max:
                max = inputdata[i,m,n]
                max_index = m*cols+n
        poolayer.y[i,r,c] = max
        poolayer.max_position[i,r,c] = max_index

@ti.kernel
def outlayer_ff(inputdata:ti.template(),outlayer:ti.template()):
    num,rows,cols = inputdata.shape
    for i in range(outlayer.outputNum):
        s = 0.0
        for j,r,c in ti.ndrange(num,rows,cols):
            k = j*rows*cols+r*cols+c
            s += inputdata[j,r,c]*outlayer.wData[i,k]
        outlayer.v[i] = s

    #softmax
    sum = 0.0
    for i in range(outlayer.outputNum):
        yi = ti.exp(outlayer.v[i]+outlayer.biasData[i])
        sum += yi
        outlayer.y[i] = yi

    for i in range(outlayer.outputNum):
        outlayer.y[i] = outlayer.y[i]/sum


#前向传播
def cnnff(cnn,inputdata):
    #cnn：卷积网络实例；inputdata：输入图像
    cov_layer_ff(inputdata,cnn.CovLayer_1)

    pool_layer_ff(cnn.CovLayer_1.y,cnn.PoolLayer_1)

    cov_layer_ff(cnn.PoolLayer_1.y,cnn.CovLayer_2)

    pool_layer_ff(cnn.CovLayer_2.y,cnn.PoolLayer_2)

    outlayer_ff(cnn.PoolLayer_2.y,cnn.OutLayer)

#反向传播
# softmax->affine
@ti.kernel
def softmax_bp(outputdata:ti.template(),e:ti.template(),o:ti.template()):
    for i in range(o.outputNum):
        e[i] = o.y[i]-outputdata[i]
        o.d[i] = e[i]


# affine->s4
@ti.kernel
def full2pool_bp(o:ti.template(),s:ti.template()):
    # o: outlayer ; s: 2nd pool layer
    oh = s.outH
    ow = s.outW
    for i in range(s.outChannels):
        for r in range(oh):
            for c in range(ow):
                wInd = i*oh*ow + r*ow +c
                for j in range(o.outputNum):
                    s.d[i,r,c] = s.d[i,r,c] + o.d[j]*o.wData[j,wInd]

@ti.func
def maxUpSample(S,i):
    #S.matC3e.fill(0.)
    num,rows,cols = S.d.shape
    mpsize = S.mapSize  # upr == upc

    out_r = rows*mpsize
    out_c = cols*mpsize
    for j,k in ti.ndrange(rows,cols):
        index_r = int(S.max_position[i, j, k] / out_c)
        index_c = int(S.max_position[i, j, k] % out_c)
        S.matC3e[index_r, index_c] = S.d[i, j, k]


@ti.func
def sigma_derivation(num):
    temp = 0
    if num>0:
        temp = 1
    return temp

@ti.kernel
def pool2cov_bp(S:ti.template(),C:ti.template()):
    # S: pool Layer
    # C: Cov Layer
    num,rows,cols = C.d.shape
    matC3e_r, matC3e_c = S.matC3e.shape
    for i in range(C.outChannels):
        for x,y in ti.ndrange(matC3e_r, matC3e_c):
            S.matC3e[x,y] = 0.
        maxUpSample(S,i)

        for r,c in ti.ndrange(rows,cols):
            C.d[i, r, c] = S.matC3e[r, c] * sigma_derivation(C.y[i, r, c])


@ti.func
def flip_kernel(C,i,j): 
    # 0-reverse matrix ; 1-orig; 2-flip
    for x in ti.static(range(C.mapSize)):
        for y in ti.static(range(C.mapSize)):
            C.mat_field[1][x,y] = C.mapData[i,j,x,y]

    C.mat_field[2] = C.mat_field[0]@C.mat_field[1]@C.mat_field[0]
    for x in ti.static(range(C.mapSize)):
        for y in ti.static(range(C.mapSize)):
            C.flipmap[x,y] = C.mat_field[2][x,y]

@ti.func
def cov(C,i,j):
    num,rows,cols = C.d.shape #8*8 ---fill---> 16*16
    mpsize = C.mapSize

    coor_r,coor_c = C.coor.shape #12*12
    fill_r,fill_c = C.fill_d.shape

    r_start = (mpsize-1)/2
    c_start = (mpsize-1)/2
    fill_start_r = mpsize-1
    fill_start_c = mpsize-1

    flip_kernel(C,i,j) 

    # C.d[j]; flimap
    for x,y in ti.ndrange((fill_start_r,fill_start_r+rows),(fill_start_c,fill_start_c+cols)):
        C.fill_d[x,y] = C.d[j,x,y]

    for x,y in ti.ndrange(coor_r,coor_c): #12*12
        temp = 0.0
        for k,l in ti.ndrange(mpsize,mpsize):
            temp += C.fill_d[x+k,y+l]*C.flipmap[k,l]
        C.coor[x,y] = temp 

# C -> S
@ti.kernel
def cov2pool_bp(C:ti.template(),S:ti.template()):
    # C 卷积层， S 池化层
    # C.d.shape 12*8*8
    num,rows,cols = S.d.shape #6*12*12
    for i in range(C.inChannels):
        for j in range(C.outChannels):
            cov(C,i,j)
            for x,y in ti.ndrange(rows,cols):
                S.d[i,x,y] = S.d[i,x,y] + C.coor[x,y]

def cnnbp(cnn,outputdata):
    softmax_bp(outputdata,cnn.e,cnn.OutLayer)
    full2pool_bp(cnn.OutLayer,cnn.PoolLayer_2)
    pool2cov_bp(cnn.PoolLayer_2,cnn.CovLayer_2)
    cov2pool_bp(cnn.CovLayer_2,cnn.PoolLayer_1)
    pool2cov_bp(cnn.PoolLayer_1,cnn.CovLayer_1)

@ti.kernel
def update_full_para(inputdata:ti.template(),opts:ti.template(),O:ti.template()):
    num,rows,cols = inputdata.shape
    mat_size = rows*cols

    for i in range(O.outputNum):
        for j in range(O.inputNum):
            x = int(j/mat_size) #第几个输入矩阵，从0开始
            temp = int(j%mat_size)
            y = int(temp/cols) #行数
            z = int(temp%cols) #列数
            O.wData[i,j] = O.wData[i,j] - opts.alpha*O.d[i]*inputdata[x,y,z]
        O.biasData[i] =  O.biasData[i]-opts.alpha*O.d[i]

@ti.func
def cdk(inputdata,C,i,j,r,c):
    num, rows, cols = C.d.shape
    sum = 0.0
    for x,y in ti.ndrange(rows, cols):
        sum += C.d[i,x,y]*inputdata[j,r+x,c+y]
    return sum

@ti.kernel
def update_cov_para(inputdata:ti.template(),opts:ti.template(),C:ti.template()):
    # mapdata shape : inchannels,outchannels,mapsize,mapsize
    num,rows,cols = C.d.shape
    for i in range(C.outChannels):
        for j in range(C.inChannels):
            for r,c in ti.ndrange(C.mapSize,C.mapSize):
                C.mapData[j,i,r,c] = C.mapData[j,i,r,c] -opts.alpha*cdk(inputdata,C,i,j,r,c)

        d_sum = 0.0
        for x,y in ti.ndrange(rows,cols):
            d_sum += C.d[i,x,y]
        C.biasData[i] = C.biasData[i] = opts.alpha*d_sum

def cnnapplygrads(cnn,opts,inputdata):
    update_cov_para(inputdata,opts,cnn.CovLayer_1) #C1
    update_cov_para(cnn.PoolLayer_1.y,opts,cnn.CovLayer_2) #C3
    update_full_para(cnn.PoolLayer_2.y,opts,cnn.OutLayer) #O5

@ti.kernel
def clear_cov_mid_para(C:ti.template()):
    num,rows,cols = C.d.shape
    for i in range(C.outChannels):
        for r,c in ti.ndrange(rows,cols):
            C.d[i,r,c] = 0.0
            C.v[i,r,c] = 0.0
            C.y[i,r,c] = 0.0

@ti.kernel
def clear_pool_mid_para(S:ti.template()):
    num,rows,cols = S.d.shape
    for i in range(S.outChannels):
        for r,c in ti.ndrange(rows,cols):
            S.d[i,r,c] = 0.0
            S.y[i,r,c] = 0.0

@ti.kernel
def clear_out_mid_para(O:ti.template()):
    for i in range(O.outputNum):
        O.d[i] = 0.0
        O.v[i] = 0.0
        O.y[i] = 0.0

def cnnclear(cnn):
    clear_cov_mid_para(cnn.CovLayer_1)
    clear_pool_mid_para(cnn.PoolLayer_1)
    clear_cov_mid_para(cnn.CovLayer_2)
    clear_pool_mid_para(cnn.PoolLayer_2)
    clear_out_mid_para(cnn.OutLayer)


# 读取数据集
import numpy as np
import struct
import matplotlib.pyplot as plt
import math

def read_images(filename):
    with open(file=filename,mode='rb') as f:
        fb_data = f.read()

    offset = 0
    fmt_header = '>iiii'    # 以大端法读取4个 unsinged int32
    magic_number, num_images, num_rows, num_cols = struct.unpack_from(fmt_header, fb_data, offset)
    print('魔数：{}，图片数：{}，行数：{}，列数：{}'.format(magic_number, num_images,num_rows,num_cols))  #magic number=2051 (图像)； 2049 文本

    images_field = ti.field(dtype=ti.f64,shape=(num_images,num_rows,num_cols))

    offset += struct.calcsize(fmt_header)
    fmt_image = '>' + str(num_rows * num_cols) + 'B'

    images = np.empty((num_images, num_rows, num_cols),dtype=np.float64)
    for i in range(num_images):
        im = struct.unpack_from(fmt_image, fb_data, offset)
        images[i] = np.array(im).reshape((num_rows, num_cols))
        offset += struct.calcsize(fmt_image)

    #print(type(num_rows))
    return images

trian_image_file_name = 'handwrite_data/train-images.idx3-ubyte'
train_images = read_images(trian_image_file_name)/255
#print(train_images[0,:,:],'pixel')

def read_labels(filename):
    with open(file=filename,mode='rb') as f:
        fb_data = f.read()

    offset = 0
    fmt_header = '>ii'  # 以大端法读取两个 unsinged int32
    magic_number, label_num = struct.unpack_from(fmt_header, fb_data, offset)
    print('魔数：{}，标签数：{}'.format(magic_number, label_num))
    offset += struct.calcsize(fmt_header)
    labels = []
    np_labels = np.zeros((label_num, 10),dtype=np.float64)

    fmt_label = '>B'    # 每次读取一个 byte
    for i in range(label_num):
        labels.append(struct.unpack_from(fmt_label, fb_data, offset)[0])
        offset += struct.calcsize(fmt_label)

    for i in range(label_num):
        value = int(labels[i])
        np_labels[i,value] = 1.0
    return np_labels

trian_label_file_name = 'handwrite_data/train-labels.idx1-ubyte'
train_labels = read_labels(trian_label_file_name)

@ti.kernel
def generate_input_field(tf:ti.template(),arr:ti.types.ndarray()):
    for i,j in ti.ndrange(28,28):
        tf[0,i,j] = arr[i,j]


def cnntrain(cnn,inputdata,outputdata,opts,train_num):
    cnn.L = ti.field(ti.float64,shape=(train_num,))
    input_field = ti.field(dtype=ti.f64,shape=(1,28,28))
    output_field = ti.field(dtype=ti.f64,shape=(10,))
    for e in range(opts.numepochs):
        for n in range(train_num):
            opts.alpha = 0.03 - 0.029 * n / (train_num - 1)
            generate_input_field(input_field,inputdata[n,:,:])
            output_field.from_numpy(outputdata[n,:])

            cnnff(cnn,input_field)
            cnnbp(cnn,output_field)
            cnnapplygrads(cnn,opts,input_field)

            l = 0.0
            for i in range(cnn.OutLayer.outputNum):
                l = l-output_field[i]*math.log(cnn.OutLayer.y[i]+1e-10)
            cnn.L[n] = l

            cnnclear(cnn)

            print("n={},f={},alpha={}".format(n,cnn.L[n],opts.alpha))

cnn = cnn_network(28,28)
opts = train_opts()
opts.numepochs = 1
opts.alpha = 0.03
cnntrain(cnn,train_images[:5000,:],train_labels[:5000,:],opts,5000) # train cnn by 5000 images

@ti.kernel
def max_index(f:ti.template()) -> int:
    lenth = f.shape[0]
    max_index = 0
    max_value = 0.0
    ti.loop_config(serialize=True)
    for i in range(lenth):
        if f[i] > max_value:
            max_value = f[i]
            max_index = i
    return max_index

def cnntest(cnn,inputdata,outputdata,tst_num):
    incorrectnum = 0
    tinput_field = ti.field(dtype=ti.f64,shape=(1,28,28))
    toutput_field = ti.field(dtype=ti.f64,shape=(10,))
    for n in range(tst_num):
        generate_input_field(tinput_field, inputdata[n, :, :])
        toutput_field.from_numpy(outputdata[n, :])
        cnnff(cnn,tinput_field)
        y_max_index = max_index(cnn.OutLayer.y)
        tag_max_index = max_index(toutput_field)
        if y_max_index != tag_max_index:
            incorrectnum += 1
            print("n:{},识别失败".format(n))
        else:
            print("n:{},识别成功".format(n))
        cnnclear(cnn)
    print("incorrect num:{}".format(incorrectnum))
    return incorrectnum/tst_num

unsuccess = cnntest(cnn,train_images[30000:40000,:,:],train_labels[30000:40000,:],10000) # test cnn by 10000 images
print("成功率：{}".format((1-unsuccess)*100))


