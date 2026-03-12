import matplotlib.pyplot as plt
from sklearn import linear_model
from scipy import stats
import copy

# Dados

def calcX(i:int):
   ii=[]
   for n in range(i):
       nn=[]
       xxx=float(n)*0.1
       nn.append(copy.copy(xxx))
       xx=float(n)*2.25
       nn.append(copy.copy(xx))
       ii.append(copy.copy(nn))
   return ii
def calcY(X):
    ii=[]
    for n in X:
        xx=n[0]+n[1]
        ii.append(copy.copy(xx))
    return ii
def prints(tt):
    for t in tt:
      print(int(t),end=" , ")
X=calcX(20)
XX=calcX(40)
y=calcY(X)
yy=calcY(XX)
print(yy)
print("-"*40)
regr = linear_model.LinearRegression()
regr.fit(X, y)
tt=[]

tt=regr.predict(XX)



prints(tt)