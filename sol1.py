# Q1. Load the dataset into a pandas DataFrame and show:
# • Total number of matches
# • Column names
# • First 5 rows of data
# • Describe the data


import pandas as pd

df=pd.read_csv('alansijok/ipl.csv')

print(f'Total matches are {len(df)}')

print(df.iloc[:0])

print(df.head())

print(df.describe())


# Q2. Which player has won the most “Player of the Match” awards in games decided on the final ball?
# (i.e., matches won by just 1 run or 1 wicket).


runs=df[df["win_by_runs"]==1 ]
wickets=df[df["win_by_wickets"]==1]

print(runs["player_of_match"].mode)
print(wickets["player_of_match"].mode)

# Q3. At Wankhede Stadium, is it more common to win by batting first (runs) or by batting second
# (wickets)?

ven=df[df['venue']=='Wankhede Stadium']

x=ven[ven['win_by_runs']>0]
y=ven[ven['win_by_wickets']>0]

x["win_by_runs"]
y["win_by_wickets"]

if len(x)>len(y):
    print("Batting First wins more")
else:
    print("Bowling First wins more")


# Q4. Which team has the highest number of wins where the victory margin was greater than 50 runs?


morethan=df[df["win_by_runs"]>50]

print(morethan["winner"].mode())

# Q5. How many times has the team that won the toss also set a target and won the match?

toss_bt_win=df[df["toss_winner"]==df["winner"]]
print(len(toss_bt_win["toss_decision"]=="bat"))

# Q6. Which of the two umpires (umpire1 or umpire2) has officiated more matches involving the
# Kolkata Knight Riders?



