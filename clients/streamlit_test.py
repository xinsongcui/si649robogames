import streamlit as st
import time, json
import numpy as np
import altair as alt
import pandas as pd
import Robogame as rg
import networkx as nx
import matplotlib.pyplot as plt

# let's create two "spots" in the streamlit view for our charts
text = st.empty()
status = st.empty()
predVis = st.empty()
partVis = st.empty()
networkVis= st.empty()
treeVis = st.empty()

name = text.text_input("Enter robot number")

# create the game, and mark it as ready
game = rg.Robogame("bob")
game.setReady()

# wait for both players to be ready
while(True):	
	gametime = game.getGameTime()
	timetogo = gametime['gamestarttime_secs'] - gametime['servertime_secs']
	
	if ('Error' in gametime):
		status.write("Error"+str(gametime))
		break
	if (timetogo <= 0):
		status.write("Let's go!")
		break
	status.write("waiting to launch... game will start in " + str(int(timetogo)))
	time.sleep(1) # sleep 1 second at a time, wait for the game to start


# run 100 times
for i in np.arange(0,101):
	# sleep 6 seconds

	for t in np.arange(0,6):
		status.write("Seconds to next hack: " + str(6-t))
		time.sleep(1)

	# update the hints

	hints = game.getHints()


	# create a dataframe for the time prediction hints
	df1 = pd.DataFrame(game.getAllPredictionHints())


	# if it's not empty, let's get going
	if (len(df1) > 0):
		# create a plot for the time predictions (ignore which robot it came from)	
		if name:
			df1 = df1[df1["id"] == int(name)]
			c1 = alt.Chart(df1).mark_circle().encode(
				alt.X('time:Q',scale=alt.Scale(domain=(0, 100))),
				alt.Y('value:Q',scale=alt.Scale(domain=(0, 100)))
			)
		else:
			c1 = alt.Chart(df1).mark_circle().encode(
				alt.X('time:Q',scale=alt.Scale(domain=(0, 100))),
				alt.Y('value:Q',scale=alt.Scale(domain=(0, 100))),
				tooltip=['time', 'value', 'id']
			)
		# write it to the screen
		predVis.write(c1)

	# get the parts
	df2 = pd.DataFrame(game.getAllPartHints())

	# we'll want only the quantitative parts for this
	# the nominal parts should go in another plot
	quantProps = ['Astrogation Buffer Length','InfoCore Size',
		'AutoTerrain Tread Count','Polarity Sinks',
		'Cranial Uplink Bandwidth','Repulsorlift Motor HP',
		'Sonoreceptors']

	# if it's not empty, let's get going
	if (len(df2) > 0):
		df2 = df2[df2['column'].isin(quantProps)]
		c2 = alt.Chart(df2).mark_circle().encode(
			alt.X('column:N'),
			alt.Y('value:Q',scale=alt.Scale(domain=(-100, 100)))
		)
		partVis.write(c2)
	
	#network plot
	network = game.getNetwork()
	socialnet = nx.node_link_graph(network)
	
	plt.figure(figsize=(20,10))
	fig, ax = plt.subplots()
	if name:
		subgraph =  socialnet.subgraph(nx.bfs_tree(socialnet, int(name), depth_limit = 1).nodes())
		list_degree=list(subgraph.degree())
		nodes,degree = map(list, zip(*list_degree)) 
		color_map =  ['red' if node == int(name) else 'green' for node in subgraph]
		nx.draw(subgraph, nodelist=nodes, node_size=[(v * 20)+1 for v in degree], node_color=color_map, with_labels=True)
	else:
		list_degree=list(socialnet.degree())
		nodes,degree = map(list, zip(*list_degree)) 
		color_map = ['red' for node in socialnet]
		nx.draw(socialnet, nodelist=nodes, node_size=[(v * 20)+1 for v in degree], node_color=color_map, with_labels=True)

	networkVis.pyplot(fig) 
	

	#tree plot
	tree = game.getTree()
	genealogy = nx.tree_graph(tree)
	fig, ax = plt.subplots()
	nx.draw_kamada_kawai(genealogy)
	treeVis.pyplot(fig) 