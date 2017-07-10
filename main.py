import re
from os import walk
import settings

# We first define two functions to be used in the search: find_kwic - the main function and its helper function regex_builder

def find_kwic(item, regexes, shell_nouns):
	"""This function takes the location of a vertically annotated text of COCA/COHA
	and transforms it to the form [['word', 'lemma', 'POS'], ['word2', 'lemma2', 'POS2'], ...]
	As a second argument the regex objects to be used in the search are passed
	(they are built outside this function to avoid building them again and again).
	As a third argument, a list of shell nouns is passed, taken from 'settings.py'
	It first filters only the contexts around shell nouns to speed up the subsequent regex. 
	Afterwards, matching results are extracted and converted into a human-readable form.
	"""
	f = open(item, "r")
	text = [x.split() for x in f.readlines()]																	# read the file, transform to list of lists
	f.close()
	
	shell_noun_locations = [id for id in range(len(text)) if text[id][0] in shell_nouns]						# find out where in the text do we find shell nouns
	shell_noun_locations = [[x-7, x+7] for x in shell_noun_locations]											# expand the context around the shell nouns to allow the regex to work
	shell_noun_locations = [[x,y] if x >= 0 else [0,y] for x,y in shell_noun_locations]							# make sure the range does not get out of the list (left side)
	shell_noun_locations = [[x,y] if y <= len(text) else [x,len(text)] for x,y in shell_noun_locations]			# make sure the range does not get out of the list (right side)
	
	contexts = [text[x:y] for x,y in shell_noun_locations]														# extract the relevant contexts from the text
	contexts = [x for x in contexts if x[2] != "y"]																# remove punctuation
	horizontal = [["_".join(x) for x in item] for item in contexts]												# convert to horizontal markup to allow the regex search
	horizontal = [x+(5*["0_0_0"]) for x in horizontal]															# add the dummy 0_0_0 to prevent overlap
	horizontal = " ".join([" ".join(context) for context in horizontal])										# transform to a plain text
	del shell_noun_locations, contexts, text																	# remove shell_noun_locations, text and contexts from the memory
	
	entries = [regex.findall(horizontal) for regex in regexes]													# for each shell noun find the fitting contexts
	entries = [item for sublist in entries for item in sublist]													# transform from list of lists to list											
	entries = [re.sub("_\S+|0_0_0", "" ,x) for x in entries]													# remove tags
	
	return entries

def regex_builder(shell_noun):
	"""Takes a shell noun, builds a regex around it, compiles and returns it."""
	shell_noun = shell_noun + "\S+"																												# append the regex for lemma + tag to the shell noun
	formula = "\S+\s\S+\s\S+_\S+_v[^b]\S+\s\S+_\S+_a\S+\s" + shell_noun + "\sthat_\S+\s\S+_\S+_p\S+\s\S+_\S+_v\S+\S+\s\S+\s"					# V + art. + shell + that + PRO + V
	formula += "|\S+\s\S+\s\S+_\S+_v[^b]\S+\s\S+_\S+_a\S+\s" + shell_noun + "\sthat_\S+\s\S+_\S+_ex\s\S+_\S+_v\S+\S+\s\S+\s"					# V + art. + shell + that + there + V
	formula += "|\S+\s\S+\s\S+_\S+_v[^b]\S+\s\S+_\S+_a\S+\s" + shell_noun + "\sthat_\S+\s\S+_\S+_n\S+\s\S+_\S+_v\S+\S+\s\S+\s"					# V + art. + shell + that + N + V
	formula += "|\S+\s\S+\s\S+_\S+_v[^b]\S+\s\S+_\S+_a\S+\s" + shell_noun + "\sthat_\S+\s\S+_\S+_n\S+\s\S+_\S+_n\S+\s\S+_\S+_v\S+\S+\s\S+\s"	# V + art. + shell + that + N + N + V
	formula += "|\S+\s\S+\s\S+_\S+_v[^b]\S+\s\S+_\S+_a\S+\s" + shell_noun + "\sthat_\S+\s\S+_\S+_a\S+\s\S+_\S+_n\S+\s\S+_\S+_v\S+\S+\s\S+\s"	# V + art. + shell + that + art + N + V
	formula += "|\S+\s\S+\s\S+_\S+_v[^b]\S+\s\S+_\S+_a\S+\s" + shell_noun + "\sthat_\S+\s\S+_\S+_d\S+\s\S+_\S+_n\S+\s\S+_\S+_v\S+\S+\s\S+\s"	# V + art. + shell + that + det + N + V
	
	regex = re.compile(formula)																					# compile the regex
	
	return regex

regexes = [regex_builder(noun) for noun in settings.shell_nouns]												# build regexes for all shell nouns		
	
# Having defined the main functions and built the regex objects, here the I/O is handled, first making a list of all files to be searched in,
# then processing each file and saving the output in one file	

items = []																										# initialize the list of files to search in
for (dirpath, dirnames, filenames) in walk(settings.inp_location):												# for loop to create the list of all files in the location
	items.extend(filenames)
	items = [(settings.inp_location + x, regexes, settings.shell_nouns)  for x in items if x.endswith(".txt")]	# only .txt files will be used, add path, regexes and shell nouns
	break

def multi_wrapper(args):																						# a wrapper allowing to pass multiple arguments to multiprocessing pool
	return find_kwic(*args)
	
if __name__ == "__main__":
	from time import localtime, strftime
	t = strftime("%a, %d %b %Y %H:%M:%S +0000", localtime())
	print(t)
	print("Starting...")
	from multiprocessing import Pool, cpu_count																	# import multi-core support
	pool = Pool(cpu_count())																					# set up [number of cores] processes
	results = pool.map(multi_wrapper, items)																	# map the input on the cores			
	
	while isinstance(results[0], list):																			# flatten the results to a simple list
		results = [item for sublist in results for item in sublist]
	results	= [x for x in results if x != []]																	# remove empty results
	results = "\n".join(results)																				# list --> string

	out = open(settings.out_location + "output.txt", "w+")														# open output file
	out.write(results)																							# save results
	out.close()
	t = strftime("%a, %d %b %Y %H:%M:%S +0000", localtime())
	print(t)
	print("Done!")