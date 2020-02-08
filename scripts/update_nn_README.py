import sys, os, re, shutil, subprocess


def code_removed(md_content):
	return re.sub("(```.*?```)", "", md_content, flags=re.S)

def generate_notebook(src_file, dst_file):
	filesdirname = os.path.basename(dst_file).split(".")[0] +"_files"
	try:
		shutil.rmtree(os.path.dirname(src_file)+"/"+filesdirname)
	except FileNotFoundError:
		pass
	p = subprocess.Popen(["jupyter", "nbconvert", os.path.basename(src_file), "--to", "markdown", "--output", os.path.basename(dst_file)], cwd=os.path.dirname(src_file))
	p.wait()
	shutil.move(os.path.dirname(src_file)+"/"+os.path.basename(dst_file), dst_file)


g_inner_links = []
def github_inner_link(link):
	global g_inner_links

	for char in ['&', '!', '%', '*', '+']:
		link = link.replace(char, "")

	link = link.replace(" ", "-")
	link = link.lower()

	# When multiple sections have the same name, we add "-%d" in the link, as does GitHub
	k = 2
	candidate_link = link
	while candidate_link in g_inner_links:
		candidate_link = link +"-%d"%k
		k += 1
	link = candidate_link
	
	g_inner_links += [link]

	return "#"+link

def generate_toc(md_file):

	with open(md_file, "r") as fin:
		mdcontent = code_removed(fin.read())
		
	sections = re.findall(r"^([#]+)[ ]*(.+)$", mdcontent, re.MULTILINE)
	toc = ""
	for section_level, section_title in sections:
		toc += "*".rjust(len(section_level), "\t") +(" [%s](%s)"%(section_title, github_inner_link(section_title))) +"\n"
	mdcontent = "# Table of contents\n\n"+ toc +"\n"+ mdcontent

	with open(md_file, "w") as fout:
		fout.write(mdcontent)	

def convert_latex_to_SVG(md_file, dst_dir):

	with open(md_file, "r") as fin:
		mdcontent = fin.read()

	equations = re.findall("\$([^\$]*)\$", re.sub("```(.*?)```", "CODE", mdcontent, flags=re.S))

	for ke, equation in enumerate(equations):
		print(equation, "\n")

		os.system("tex2svg '"+ equation +"' > "+ dst_dir +"/equation_%d.svg"%ke)
		mdcontent = mdcontent.replace("$"+equation+"$", "![]("+ os.path.basename(md_file).replace(".md", "_files") +"/equation_%d.svg)"%ke)

	with open(md_file, "w") as fout:
		fout.write(mdcontent)


def remove_first_code_block(md_file):

	with open(md_file, "r") as fin:
		mdcontent = fin.read()
	
	mdcontent = re.sub("```(.*?)```", "", mdcontent, 1, flags=re.S)

	with open(md_file, "w") as fout:
		fout.write(mdcontent)
	

def add_header_note(md_file, text):

	with open(md_file, "r") as fin:
		mdcontent = fin.read()
	
	mdcontent = "<sup>"+ text +"</sup>\n"+ mdcontent

	with open(md_file, "w") as fout:
		fout.write(mdcontent)



# add "doc/" to the beginning of each path (img or link)
def fix_paths(md_file):

	with open(md_file, "r") as fin:
		mdcontent = fin.read()
	
	mdcontent_no_code = code_removed(mdcontent)

	# [txt](path)
	links = re.findall("(\\[[^\\]]*\\]\\([^#]{1}[^\\)]*\\))", mdcontent_no_code)
	for l in links:
		if "(http" not in l:
			mdcontent = mdcontent.replace(l, l.replace("](", "](docs/"))

	# src="path"
	mdcontent = re.sub("src=\"([^\"]+)\"", "src=\"docs/\\1\"", mdcontent)

	with open(md_file, "w") as fout:
		fout.write(mdcontent)	



def collapsed_code(md_file):

	with open(md_file, "r") as fin:
		mdcontent = fin.read()
	
	mdcontent = re.sub("(```.*?```)", "<details><summary>Expand code</summary><p>\n\n\\1\n\n</p></details>", mdcontent, flags=re.S)

	with open(md_file, "w") as fout:
		fout.write(mdcontent)



if __name__ == "__main__":

	generate_notebook("../neural_network/docs/documentation.ipynb", "../neural_network/README.md")
	generate_toc("../neural_network/README.md")
	convert_latex_to_SVG("../neural_network/README.md", "../neural_network/docs/README_files")
	collapsed_code("../neural_network/README.md")
	fix_paths("../neural_network/README.md")
	add_header_note("../neural_network/README.md", "Generated from [docs/documentation.ipynb](docs/documentation.ipynb) by [../scripts/update_nn_README.py](../scripts/update_nn_README.py).\n")

	print("\033[93m" + "Do not forget to run:\n\n\tgit add ../neural_network/docs/README_files/*\n" + "\033[0m")

