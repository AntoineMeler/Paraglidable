import matplotlib.pyplot as plt
import glob, time
import numpy as np

patterns = [("b", "tmp_trainings/*/CELLS.log"),
			("r", "bin/models/CLASSIFICATION_2.0.0/CELLS.log")]

validation_loss_col = 2

while True:
	min_val, ymin, ymax, max_length, nb =  1e10, 1e10, -1e10, 0, 0
	for pattern in patterns:
		for l in glob.glob(pattern[1]):
			with open(l, "r") as fin:
				try:
					contents = np.array([[float(v) for v in line.split(" ")] for line in fin.read().split("\n")[:-1]])
					plt.plot(contents[:,2], color=pattern[0], alpha=0.5)
					ymin = min([ymin] + contents[:,validation_loss_col].tolist())
					ymax = max(ymax, contents[:,validation_loss_col][3])
					max_length = max(max_length, contents.shape[0])
					min_val = min(min_val, np.amin(contents[:,validation_loss_col]))
					nb += 1
				except:
					print("error with", l)
	plt.title("%d, %f"%(nb, min_val))
	plt.ylim(ymin, ymax)
	plt.hlines([int(ymin*100.)/100.+0.0025*l for l in range(40)], 0, max_length-1, linestyles='dotted', linewidth=1)
	plt.savefig("plot.png", dpi=170)
	plt.clf()
	time.sleep(5)