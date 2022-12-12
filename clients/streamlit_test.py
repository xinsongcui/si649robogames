import streamlit as st
import time, json
import numpy as np
import altair as alt
import pandas as pd
import Robogame as rg
import networkx as nx
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf 
import statsmodels.api as sm
from numpy import NaN

# let's create two "spots" in the streamlit view for our charts
text = st.empty()
continue_button = st.empty()
status = st.empty()
predVis = st.empty()
barVis = st.empty()
scatterVis = st.empty()
pcaVis = st.empty()
regVis = st.empty()
partVis = st.empty()
socialVis = st.empty()
networkVis= st.empty()
treeVis = st.empty()
dataVis = st.empty()


form = text.form(key='my_form')
name = form.text_input(label='Enter robot number')
submit_button = form.form_submit_button(label='Submit')


# create the game, and mark it as ready
game = rg.Robogame("bob")
#game = rg.Robogame("123",server="roboviz.games",port=5000)
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

	tree = game.getTree()
	genealogy = nx.tree_graph(tree)

	robots = game.getRobotInfo()
	gametime = game.getGameTime()

	#dataVis.write(robots)
	robots = robots[robots['Productivity'].notnull()]
	robots = robots[(robots['expires'].notnull()) & (robots['expires'] > 0)]
	#robots = robots[robots['bets'] == -1]
	robots = robots[robots['winningTeam'] != 'Unassigned']
	robots = robots[robots['Productivity'] > 0]

	#st.write(robots)
	pred_prods = {}
	for id, row in robots.iterrows():
		predecessors = genealogy.predecessors(id)
		#successors = nx.nodes(nx.dfs_tree(genealogy, id, depth_limit = 2))
		#neighbor = [n for n in successors]
		neighbor = [n for n in predecessors]
		for n in neighbor:
			pred_prods[n] = row['Productivity']

	succ_prods = {}
	for id, val in pred_prods.items():
		neighbor = [n for n in genealogy.successors(id)]
		for n in neighbor:
			if n not in robots["id"] and n<100:
				succ_prods[n] = val
	

	source = pd.DataFrame(
    	{"id": list(succ_prods.keys()), "Productivity": list(succ_prods.values())}
	)
	
	if len(succ_prods) > 0:
		maxProd =  max(succ_prods, key=succ_prods.get)
	else:
		maxProd = -1

	#Productivitiy graph
	if len(source) > 0:
		bar = alt.Chart(source).mark_bar().encode(
			alt.X('id:N', sort = '-y'),
			alt.Y('Productivity:Q'),	
		).properties(
    		title='Productivity Inferenced from Family Tree' 
		)

		barVis.write(bar)


	if  len(df1) > 0 and maxProd in df1["id"].values:
		pred = df1[df1["id"] == maxProd]

		circle = alt.Chart(pred).mark_circle().encode(
				alt.X('time:Q',scale=alt.Scale(domain=(0, 100))),
				alt.Y('value:Q',scale=alt.Scale(domain=(0, 100)))
			).properties(
    			title='Random Number for robot: ' + str(maxProd)
			)
		scatterVis.write(circle)


	#Productivitiy from parts

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
	
	#Socaial network bar chart
	robotsInfo = game.getRobotInfo()
	robotsInfo["remains"] = robotsInfo["expires"] - gametime["curtime"]
	df_network = pd.DataFrame.from_dict(socialnet.degree)
	df_network = df_network.rename(columns = {1:"number of friends", 0:"id"})

	st.write(robotsInfo)
	#add a variable "remains" to show the remaining time
	df_network["winningTeam"] = robotsInfo["winningTeam"]
	df_network["remains"] = robotsInfo["expires"] - gametime["curtime"]

	#add a binary variable "remain" to show whether remaining time < 10s
	df_network["remain"] = df_network["remains"] 
	df_network.remain[df_network.remains <= 10] = "<= 10s"
	df_network.remain[df_network.remains >10] = "> 10s"
	st.write(df_network)
	network1 = alt.Chart(df_network, title='Number of Surrounding Nodes').mark_bar().transform_filter(
        (alt.datum.winningTeam == "Unassigned") & (alt.datum.remains >0)).encode(
        alt.X("id:N", sort=alt.EncodingSortField(field='number of friends', order='descending')),
        alt.Y("number of friends:Q"),
        alt.Color('remain:N'),
        tooltip=['id', 'number of friends', "remains"]
    )

	socialVis.write(network1)

	#tree plot
	#tree = game.getTree()
	#genealogy = nx.tree_graph(tree)
	fig, ax = plt.subplots()
	nx.draw(genealogy,with_labels=True)
	treeVis.pyplot(fig) 