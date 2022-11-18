# ti-CNN
Convolution Neural Network implemented by Taichi

## Usage
```bash
git clone git@github.com:Linus-Civil/ti-CNN.git
cd ./ti-CNN
pip install -r requirements.txt
python3 ti_cnn.py
```

## Note
- Dataset: MNIST handwritten digit database
- I selected two subsets from the original training set as the training set and test set for this code. Currently, the accuracy on the test set is about 60%.
- Expanding the training set will reduce the accuracy of the test set, which may be caused by the following two aspects
	- There are bugs in the code
	- Over-fitting
- This repo is still under development and is for reference only

