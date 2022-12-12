import streamlit as st
import time, json
import numpy as np
import altair as alt
import pandas as pd
import Robogame as rg
import networkx as nx
import matplotlib.pyplot as plt
import statsmodels.api as sm
from numpy import NaN
from sklearn.linear_model import LinearRegression

# let's create two "spots" in the streamlit view for our charts
text = st.empty()
status = st.empty()
prod1 = st.empty()
prod2 = st.empty()
prod3 = st.empty()
scatterVis = st.empty()
socialVis = st.empty()


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


	df = pd.DataFrame(game.getAllPartHints())

	if(len(df)>0):
		df_pca = pd.DataFrame(columns=df['column'].unique(),index=df['id'].unique(),dtype=float)
		for i in range(len(df)):
			df_pca.loc[df.loc[i,'id'],df.loc[i,'column']] = df.loc[i,'value']
    
	df_product = pd.DataFrame(game.getRobotInfo())
	df_pca = pd.merge(df_pca, df_product[['Productivity']].astype('float'), left_index=True, right_index=True).reset_index()

	for c in df_pca.columns:
		if df_pca[c].dtype==object:
			num_value = pd.DataFrame(df_pca.groupby(c).mean()['Productivity']).reset_index().rename(columns={'Productivity':'value'})
			df_pca = df_pca.merge(num_value, on=c, how='left').drop(columns=c).rename(columns={'value':c})
            
	old_col = df_pca[['Productivity']]
	df_pca = df_pca.drop(columns=['Productivity'])
	df_pca['Productivity'] = old_col

	def mul_reg(df_pca):
		model = sm.OLS(df_pca['Productivity'], df_pca[df_pca.columns[-3:-1]], missing='drop')
		results = model.fit()
		df_pca['Productivity_predict'] = results.predict(df_pca[results.params.keys()]) 
		return df_pca

    
	def lin_comb_reg(df_pca):
		reg_coe = pd.DataFrame(columns=['corr'],index=df_pca.columns,dtype=float)

		for f in df_pca.columns[:-1]:
			test = df_pca[[f,'Productivity']]
			test = test.dropna()
			if test.any()[0]:
				model = LinearRegression().fit(test[[f]], test['Productivity'])
				model.predict(df_pca[[f]].dropna())
				df_pca.loc[~df_pca[f].isna(),f+'_val'] = model.predict(df_pca[[f]].dropna())
				reg_coe.loc[f,'corr'] = model.score(test[[f]], test['Productivity'])

		df_pca['predict_all'] = 0
		df_pca['predict_weight'] = 0

		for f in reg_coe.dropna().index:
			df_pca.loc[~df_pca[f].isna(),'predict_all'] += df_pca.loc[~df_pca[f].isna(),f+'_val']*reg_coe.loc[f,'corr']
			df_pca.loc[~df_pca[f].isna(),'predict_weight'] += reg_coe.loc[f,'corr']
		df_pca['Productivity_predict'] = df_pca['predict_all']/ df_pca['predict_weight']
		return df_pca        
        
	if len(df_pca.dropna(axis=0)) >0:
		df_pca = mul_reg(df_pca)
	else:        
		df_pca = lin_comb_reg(df_pca)

	robot_ava = game.getRobotInfo()
	robot_ava = robot_ava[(robot_ava['expires'].notnull()) & (robot_ava['expires'] > 0) & (robot_ava['winner'] == -2)][['id','expires']]
	curtime = game.getGameTime()['curtime']
	text.write("Current Time: "+str(curtime))

	robot_ava['remain_time'] = robot_ava['expires']-curtime
       
	df_pca = pd.merge(df_pca,robot_ava,left_on='index',right_on='id',how='inner')


	vis =alt.Chart(df_pca).mark_bar().encode(
		x = alt.X('index:N',sort='-y'),
		y = alt.Y("Productivity_predict:Q"),
		color = alt.Color('remain_time:Q'),
		tooltip = alt.Tooltip(['index','Productivity_predict'])).properties(title='Productivity from features regression')    
	prod3.write(vis) 


    
	# create a dataframe for the time prediction hints
	df1 = pd.DataFrame(game.getAllPredictionHints())

	tree = game.getTree()
	genealogy = nx.tree_graph(tree)

	robots = game.getRobotInfo()
	#dataVis.write(robots)
	robots = robots[robots['Productivity'].notnull()]
	robots = robots[(robots['expires'].notnull()) & (robots['expires'] > 0)]
	#robots = robots[robots['bets'] == -1]
	robots = robots[robots['winner'] != -2]#robots = robots[robots['winner'] != 'Unassigned']
	robots = robots[robots['Productivity'] > 0]


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
		prod2.write(bar)
        
        
	# Productivitiy Combination       
	df_prod = pd.merge(source,df_pca[['index','Productivity_predict']],left_on='id',right_on='index',how='outer')
	df_prod.loc[df_prod['id'].isna(),'id'] = df_prod.loc[df_prod['id'].isna(),'index']
	df_prod.loc[df_prod['Productivity'].isna(),'Productivity'] = df_prod.loc[df_prod['Productivity'].isna(),'Productivity_predict']
	df_prod = df_prod.drop(columns=['index','Productivity_predict'])

	df_prod = pd.merge(df_prod,robot_ava,left_on='id',right_on='id',how='inner')
	vis = alt.Chart(df_prod).mark_bar().encode(
		x = alt.X('id:N',sort='-y'),
		y = alt.Y("Productivity:Q"),
		color = alt.Color('remain_time:Q'),
		tooltip = alt.Tooltip(['id','Productivity'])).properties(title='Productivity vs id')
	prod1.write(vis) 
    

#	if  len(df1) > 0 and maxProd in df1["id"].values:
	pred = df1.copy()
	robot_ava2 = game.getRobotInfo()
	robot_ava2 = robot_ava2[(robot_ava2['expires'].isnull()) | (robot_ava2['expires'] > curtime) & (robot_ava2['winner'] == -2)][['id']]
    
	pred = pd.merge(pred,robot_ava2,left_on='id',right_on='id',how='inner')

	base = alt.Chart(pred)
	selection = alt.selection_single(encodings=["x"], on="mouseover", empty="none")
	opacityCondition = alt.condition(selection,alt.value(1),alt.value(0.00000000000000000000000001))

	Vline = base.mark_rule(size=4, color="lightgray",opacity=0).encode(
		x = alt.X("time:Q"),
		opacity = opacityCondition).add_selection(selection)

	dot = base.mark_circle(size=70, color="black").encode(
		x = alt.X("time:Q"),
		y = alt.Y("value:Q"),
		opacity = opacityCondition,
		tooltip = alt.Tooltip(['id','time','value']))

	circle = base.mark_circle().encode(
			alt.X('time:Q',scale=alt.Scale(domain=(0, 100))),
			alt.Y('value:Q',scale=alt.Scale(domain=(0, 100))),
			tooltip = alt.Tooltip(['id','time','value'])
			)

	rul = alt.Chart(pd.DataFrame({'time': [curtime]})).mark_rule(color='red').encode(x='time')
    
	vis = (Vline+dot+circle+rul).interactive().resolve_axis(y="shared").properties(title='Random Number for all robots')
	scatterVis.write(vis)
    
    
    
    
	#Socaial network bar chart
	network = game.getNetwork()
	socialnet = nx.node_link_graph(network)
	df_network = pd.DataFrame.from_dict(socialnet.degree)
	df_network = df_network.rename(columns = {1:"number of friends", 0:"id"})

	df_network = pd.merge(df_network,robot_ava,left_on='id',right_on='id',how='inner')
    
	network1 = alt.Chart(df_network).mark_bar().encode(
		alt.X("id:N", sort=alt.EncodingSortField(field='number of friends', order='descending')),
		alt.Y("number of friends:Q"),
		alt.Color('remain_time:Q'),
		tooltip=['id', 'number of friends', "remain_time"]).properties(title='Number of Surrounding Nodes')
	socialVis.write(network1)