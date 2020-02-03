import os, pickle

class BinObj():

	obj_path = "./bin/data"

	@classmethod
	def save(cls, obj, name, path=None):
		if not path:
			path = cls.obj_path

		os.makedirs(path, exist_ok=True)
		with open(os.path.join(path, name) + '.pkl', 'wb') as f:
			pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)

	@classmethod
	def load(cls, name, path=None):
		if not path:
			path = cls.obj_path

		with open(os.path.join(path, name) + '.pkl', 'rb') as f:
			return pickle.loads(f.read(), encoding='latin1') # python 2 -> 3

	@classmethod
	def exists(cls, name, path=None):
		if not path:
			path = cls.obj_path

		file = os.path.join(path, name) + '.pkl'
		return os.path.isfile(file)
