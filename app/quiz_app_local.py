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

with open('quiz_data.json', 'r') as json_file:
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

def Scenarios_Polls():
    '''
    This function selects the scenarios that will seen to the users.
    Every user will get 3 scenarios (27 questions) with the lowest amount of times that concluded in the polls.
    :return: The 3 scenarios that will conclude in the poll. (27 questions)
    list of scenarios
    '''
    polls_quiz_data=[]
    query_amount_scenarios=("Select Scenario,Count(Scenario) AS Amount_Scen_Answer from answers group by(Scenario) "
                            "order by Amount_Scen_Answer DESC;")
    cursor.execute(query_amount_scenarios)
    Scenario_answered = cursor.fetchall()
    if len(Scenario_answered)<4:
        print(len(Scenario_answered))
        with open('scenarios.json', 'r') as json_file:
            scenarios = json.load(json_file)

        Scenario_answered = dict(sorted(list(scenarios.items()), key=lambda x: x[1])[:2])
        Scenario_answered=list(Scenario_answered.keys())
        #update the amount of scenarios
        scenarios.update(Counter(Scenario_answered))
        with open('scenarios.json', 'w') as json_file:
            json.dump(scenarios, json_file, indent=4)
    else:
        Scenario_answered = dict(sorted(Scenario_answered, key=lambda x: x[1])[:2])
        print(Scenario_answered)
        Scenario_answered = list(Scenario_answered.keys())

    print(Scenario_answered)
    lst_scenarios=[]
    for scenario in Scenario_answered:
        lst_scenarios+=[scenario[0]] * 18
    for dict_question in quiz_data:
        for key in dict_question:
            if key in lst_scenarios :
                polls_quiz_data.append(dict_question[key])
    return polls_quiz_data , lst_scenarios

quiz_data, scenarios = Scenarios_Polls()
index_scen=0

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

    fig, ax = plt.subplots(figsize=(10, 6))  # Increase the figure size
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
    return fig

# Function to save the answer and response time to the database
def save_response(Costant_String_Each_User,Scenario, selected_choice, time_taken, winner, utility_choice):
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
        cursor.execute('''INSERT INTO answers (User_ID,Scenario, selected_choice, time_taken,winner,utility_choice)
                          VALUES (%s,%s, %s, %s,%s, %s)''', (Costant_String_Each_User,Scenario, selected_choice, time_taken,
                                                             winner, utility_choice))
        conn.commit()
    except MySQLdb.Error as e:
        print(f"An error occurred: {e}")

# Function to check the selected answer and provide feedback
def check_answer(choice_idx):
    '''
    Checking if the user won/not. In addition, stop the timer after the user vote
    :param choice_idx:
    :return:Saving the response in DB.
    '''
    global start_time, countdown_time
    global index_scen
    Scenario=scenarios[index_scen]
    index_scen+=1

    selected_choice = quiz_data[current_question]["choices"][choice_idx]["text"]
    winner = quiz_data[current_question]["winner"]
    utility_choice=0
    if selected_choice == 'No Vote' or selected_choice == winner:
        utility_choice = quiz_data[current_question]["choices"][choice_idx]['coins']
    end_time = time.time()
    time_taken = end_time - start_time

    # Save response to database
    save_response(Costant_String_Each_User,Scenario, selected_choice, time_taken,winner,utility_choice)

    # Disable all choice buttons and enable the next button
    for button in choice_btns:
        button.config(state="disabled")
    next_btn.config(state="normal")

    # Stop the timer
    countdown_time = -1

# Function to update the countdown timer
def update_timer():
    '''
    30 Seconds to vote for one candidate (or not- No Vote option). Stop the timer when the user voted.
    Else, the poll continue.
    '''
    global countdown_time
    if countdown_time > 0:
        timer_label.config(text=f"Time left: {countdown_time} seconds")
        countdown_time -= 1
        root.after(1000, update_timer)
    elif countdown_time == 0:
        next_question()

# # Function to display the current question and choices
def show_question():
    '''
    Shows and design the screen with 4/3 candidates options
    :return:
    '''
    global start_time, countdown_time, canvas, choice_btns
    start_time = time.time()
    countdown_time = 30

    question = quiz_data[current_question]
    qs_label.config(text=question["question"])

    # Destroy existing buttons
    for btn in choice_btns:
        btn.destroy()
    choice_btns = []

    # Display the choices on the buttons
    choices = question["choices"]
    num_choices = len(choices)
    for i in range(num_choices):
        choice_text = f"{choices[i]['text']} - 💰 {choices[i]['coins']} coins"
        button = ttk.Button(
            frame,
            text=choice_text,
            command=lambda i=i: check_answer(i)
        )
        button.grid(row=1, column=i, padx=20, pady=10)
        choice_btns.append(button)

    # Clear the feedback label and disable the next button
    feedback_label.config(text="")
    next_btn.config(state="disabled")
    #difference_votes_label.config(text=f"Difference Votes: {int(choices[0]['Different Votes'])} , ")

    fig = plot_bar_graph(choices)
    canvas.get_tk_widget().pack_forget()  # Remove old canvas
    canvas = FigureCanvasTkAgg(fig, master=bar_frame)
    canvas.draw()
    canvas.get_tk_widget().pack()

    update_timer()
#
# # Function to move to the next question
def next_question():
    '''
    Move to the next question after the user press "Next" button.
    When the user answered to the last question of the poll, he will get the message "quiz completed" and will exit from the poll system.
    :return:
    '''
    global current_question
    current_question += 1
    if current_question < len(quiz_data):
        show_question()
    else:
        messagebox.showinfo("Quiz Completed", "Quiz Completed!")
        root.destroy()

# Create the main window
root = tk.Tk()
root.title("Trivia App")
root.geometry("800x600")
style = Style(theme="flatly")

# Configure the font size for the question and choice buttons
style.configure("TLabel", font=("Helvetica", 20))
style.configure("TButton", font=("Helvetica", 16))

# Create the question label
qs_label = ttk.Label(
    root,
    anchor="center",
    wraplength=500,
    padding=10
)
qs_label.pack(pady=10)

# Create the choice buttons frame
frame = ttk.Frame(root)
frame.pack(pady=20)

choice_btns = []

# Create the feedback label
feedback_label = ttk.Label(
    root,
    anchor="center",
    padding=10
)
feedback_label.pack(pady=10)

# Create the next button
next_btn = ttk.Button(
    root,
    text="Next",
    command=next_question,
    state="disabled"
)
next_btn.pack(pady=10)

# Create the timer label
timer_label = ttk.Label(
    root,
    anchor="center",
    padding=10
)
timer_label.pack(pady=10)

# difference_votes_label = ttk.Label(
#     root,
#     anchor="center",
#     padding=10
# )
# difference_votes_label.pack(pady=10)

# Initialize the current question index
current_question = 0

# Create a frame for the bar graph
bar_frame = ttk.Frame(root)
bar_frame.pack(pady=20)

# Plot the initial bar graph
fig = plot_bar_graph(quiz_data[0]["choices"])

# Embed the plot in the Tkinter window
canvas = FigureCanvasTkAgg(fig, master=bar_frame)
canvas.draw()
canvas.get_tk_widget().pack()

# Show the first question
show_question()
# Start the main event loop
root.mainloop()

# Close the database connection when the app closes
conn.close()
