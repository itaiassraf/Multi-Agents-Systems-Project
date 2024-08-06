import tkinter as tk
from tkinter import ttk, messagebox
from ttkbootstrap import Style
import time
import MySQLdb
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import json
import random
import string
from collections import Counter
import threading
from flask import Flask, request, render_template_string, redirect, url_for, send_file
from pyngrok import ngrok
import io
import base64
import pandas as pd

app = Flask(__name__)

# Sample data
df_polls=pd.read_excel("Project- polls distribution.xlsx")
with open('quiz_data1.json', 'r') as json_file:
    quiz_data = json.load(json_file)
#User Id
Costant_String_Each_User = ''.join(random.choices(string.digits, k=10))

# Create a database connection
conn = MySQLdb.connect(
    host="localhost",
    user="root",
    password="vtjv2zYh",
    database="quiz"
)
cursor = conn.cursor()

query_user_id_count = "SELECT Count(Distinct(User_ID)) from answers;"
cursor.execute(query_user_id_count)
amount_of_users = cursor.fetchone()[0]

query = "SELECT * FROM answers"
df = pd.read_sql(query, conn)

# Save the DataFrame as an Excel file
df.to_excel('answers.xlsx', index=False)

def Scenarios_Polls():
    '''
    This function selects the scenarios that will seen to the users.
    Every user will get 3 scenarios (27 questions) with the lowest amount of times that concluded in the polls.
    :return: The 3 scenarios that will conclude in the poll. (27 questions)
    list of scenarios
    '''
    polls_quiz_data = []
    query_amount_scenarios = ("Select Scenario,Count(Scenario) AS Amount_Scen_Answer from answers group by(Scenario) "
                              "order by Amount_Scen_Answer DESC;")
    cursor.execute(query_amount_scenarios)
    Scenario_answered = cursor.fetchall()
    if len(Scenario_answered) < 4:
        print(len(Scenario_answered))
        with open('scenarios.json', 'r') as json_file:
            scenarios = json.load(json_file)

        Scenario_answered = dict(sorted(list(scenarios.items()), key=lambda x: x[1])[:2])
        Scenario_answered = list(Scenario_answered.keys())
        #update the amount of scenarios
        scenarios.update(Counter(Scenario_answered))
        with open('scenarios.json', 'w') as json_file:
            json.dump(scenarios, json_file, indent=4)
    else:
        Scenario_answered = dict(sorted(Scenario_answered, key=lambda x: x[1])[:2])
        print(Scenario_answered)
        Scenario_answered = list(Scenario_answered.keys())

    print(Scenario_answered)
    lst_scenarios = []
    for scenario in Scenario_answered:
        lst_scenarios += [scenario[0]] * 18
    for dict_question in quiz_data:
        for key in dict_question:
            if key in lst_scenarios:
                polls_quiz_data.append(dict_question[key])
    return polls_quiz_data, lst_scenarios


quiz_data, scenarios = Scenarios_Polls()
print(scenarios)
index_scen = 0

# Track the start time of each question
start_time = None
countdown_time = 30


# Helper function to display bar graph
def plot_bar_graph(choices):
    '''
    This function displays the distribution of the poll votes for each candidate.
    :param choices: The candidates with their respective votes and prizes.
    :return: A graph showing the vote distribution.
    '''

    labels = [choice["text"] for choice in choices if choice["text"] != 'No Vote']
    votes = [choice["votes"] for choice in choices if choice["votes"] != -1]
    total_votes = sum(votes)

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(labels, votes, color=labels)

    # Ensure a minimum y-axis limit to make bars visible
    min_ylim = max(5, total_votes // 10)
    ax.set_ylim(0, max(total_votes, min_ylim))  # Set the y-axis limit

    ax.set_ylabel('Votes')
    ax.set_title('Vote Distribution')

    # Attach the value on top of each bar with a large font in blue
    for bar in bars:
        height = int(bar.get_height())  # Convert height to integer
        ax.annotate('{}'.format(height),
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 5),  # Adjust the vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom',
                    fontsize=14, color='blue')  # Increase the font size

    fig.tight_layout()  # Adjust the layout to make room for labels
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    return base64.b64encode(img.getvalue()).decode()


# Function to save the answer and response time to the database
def save_response(Costant_String_Each_User, Scenario, selected_choice, time_taken, winner, utility_choice,
                  sample_size, diff_type, most_preffer,least_preffer):
    '''
    The function save for each question details about the question and the user.
    :param Costant_String_Each_User: User ID. 10 digits number
    :param Scenario: A-G. The question's scenario
    :param selected_choice: The candidate that the user chose
    :param time_taken: The amount of time until the user vote
    :param winner: The winner candidate of the poll in reality.
    :param utility choice: The utility will be if the user select "No Vote" and he will given the utility of no vote.
    If he chose the loser- will get 0 coins, and if chose the winner- will get the utility of the winner candidate.
    :return: Insert to DB a row that contains those params.
    '''

    try:
        cursor.execute('''INSERT INTO answers (User_ID, Scenario, selected_choice, time_taken,winner,utility_choice,
         sample_size, diff_type, most_preffer,least_preffer)
                          VALUES (%s,%s, %s, %s,%s, %s,%s,%s, %s, %s)''',
                       (Costant_String_Each_User, Scenario, selected_choice, time_taken,
                        winner, utility_choice, sample_size, diff_type, most_preffer,least_preffer))
        conn.commit()
    except MySQLdb.Error as e:
        print(f"An error occurred: {e}")


@app.route('/')
def index():
    return render_template_string('''
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Trivia App</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background-color: #f0f0f0;
                    color: #333;
                    text-align: center;
                    padding: 20px;
                }
                .container {
                    background-color: #fff;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
                    max-width: 600px;
                    margin: 0 auto;
                }
                a {
                    display: inline-block;
                    margin: 20px 0;
                    padding: 10px 20px;
                    background-color: #007bff;
                    color: #fff;
                    text-decoration: none;
                    border-radius: 5px;
                }
                a:hover {
                    background-color: #0056b3;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Welcome to the Voting Experiment ! </h1>
                <a href="/questions/0">Start Quiz</a>
            </div>
        </body>
        </html>
    ''')


@app.route('/questions/<int:question_id>', methods=['GET', 'POST'])
def question(question_id):
    if request.method == 'POST':
        index_poll=question_id
        user_id = Costant_String_Each_User
        choice_idx = int(request.form['choice'])
        scenario = scenarios[question_id]
        selected_choice = quiz_data[question_id]["choices"][choice_idx]["text"]
        winner = quiz_data[question_id]["winner"]
        if question_id>=18:
            index_poll=question_id-18
        print(index_poll)
        df_polls_filter= df_polls[df_polls['Scenario'] == scenario]
        sample_size = list(df_polls_filter['sample size'])[index_poll]
        diff_type = list(df_polls_filter['Diff Type'])[index_poll]
        most_prefer = list(df_polls_filter['Pref 1'])[index_poll]
        least_prefer = list(df_polls_filter['Pref 2'])[index_poll]
        utility_choice = 0
        if selected_choice == 'No Vote' or selected_choice == winner:
            utility_choice = quiz_data[question_id]["choices"][choice_idx]['coins']

        start_time = float(request.form['start_time'])
        end_time = time.time()
        time_taken = end_time - start_time

        save_response(user_id, scenario, selected_choice, time_taken, winner, utility_choice,
                      sample_size,diff_type,most_prefer,least_prefer)
        next_question_id = question_id + 1
        if next_question_id < len(quiz_data):
            return redirect(url_for('question', question_id=next_question_id))
        else:
            return render_template_string('''
                <h1>Quiz Completed!</h1>
                <p>Thank you for participating.</p>
            ''')

    question = quiz_data[question_id]
    graph_data = plot_bar_graph(question["choices"])
    start_time = time.time()
    question_html = f'''
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Trivia Question</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f0f0f0;
                    color: #333;
                    text-align: center;
                    padding: 20px;
                }}
                .container {{
                    background-color: #fff;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
                    max-width: 600px;
                    margin: 0 auto;
                }}
                .question {{
                    font-size: 24px;
                    margin-bottom: 20px;
                }}
                .choices {{
                    list-style: none;
                    padding: 0;
                }}
                .choices li {{
                    margin-bottom: 10px;
                }}
                .choices input[type="radio"] {{
                    margin-right: 10px;
                }}
                .submit-btn {{
                    padding: 10px 20px;
                    background-color: #007bff;
                    color: #fff;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                }}
                .submit-btn:hover {{
                    background-color: #0056b3;
                }}
                .timer {{
                    font-size: 20px;
                    margin-bottom: 20px;
                }}
            </style>
            <script>
                let timeLeft = 30;
                let startTime = {start_time};
                function countdown() {{
                    if (timeLeft == 0) {{
                        document.getElementById("quiz-form").submit();
                    }} else {{
                        document.getElementById("timer").innerHTML = timeLeft + " seconds remaining";
                        timeLeft--;
                        setTimeout(countdown, 1000);
                    }}
                }}
                window.onload = countdown;
            </script>
        </head>
        <body>
            <div class="container">
                <div class="question">{question["question"]}</div>
                <form id="quiz-form" method="POST">
                    <input type="hidden" name="start_time" value="{start_time}">
                    <ul class="choices">
    '''
    for idx, choice in enumerate(question["choices"]):
        question_html += f'''
                        <li><label><input type="radio" name="choice" value="{idx}"> {choice["text"]} - 💰 {choice["coins"]} coins</label></li>
        '''
    question_html += '''
                    </ul>
                    <input type="submit" class="submit-btn" value="Submit">
                </form>
                <div id="timer" class="timer">30 seconds remaining</div>
                <img src="data:image/png;base64,{{ graph_data }}" alt="Vote Distribution" style="max-width: 100%; height: auto;">
            </div>
        </body>
        </html>
    '''
    return render_template_string(question_html, graph_data=graph_data)


@app.route('/plot/<int:question_id>')
def plot(question_id):
    question = quiz_data[question_id]
    img = plot_bar_graph(question["choices"])
    return send_file(img, mimetype='image/png')


def start_ngrok():
    public_url = ngrok.connect(5000).public_url
    print(f"ngrok URL: {public_url}")


if __name__ == '__main__':
    # Start ngrok tunnel
    threading.Thread(target=start_ngrok).start()
    # Run Flask app
    app.run(port=5000)

    # Close the database connection when the app closes
    conn.close()
