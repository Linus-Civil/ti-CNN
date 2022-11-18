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
- Relationship between accuracy of CNN on test set and size of training set
	- 1000 training images &rarr; 81.77%
	- 2000 training images &rarr; 86.17%
	- 3000 training images &rarr;  89.07%
	- 4000 training images &rarr; 84.15%
	- 5000 training images  &rarr; 91.88%
	- 10000  training images  &rarr; 91.98%
	- 60000  training images  &rarr; 86.60%
- I am not a major in artificial intelligence, and only show what I just learned. The prediction accuracy on the test set is not bad, but there may be BUG in the code, for reference only.

