import sqlite3
from bs4 import BeautifulSoup
import re

class Roll:
    def __init__(self, player_name, dice_rolled, roll_result):
        self.player_name = player_name
        self.base_dice = dice_rolled
        self.roll_result = roll_result

    def __str__(self):
        return f'{self.player_name} rolled {self.base_dice} and got {self.roll_result}'

# Create or connect to a SQLite database
conn = sqlite3.connect('rolls.db')
cursor = conn.cursor()

# drop all tables
cursor.execute('DROP TABLE IF EXISTS rolls')

## Create a table if it doesn't already exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS rolls (
        player_name TEXT,
        dice INTEGER,
        result INTEGER
    )
''')

# Read the content of the HTML file
with open('chat_log.html', 'r', encoding='utf-8') as file:
    html_content = file.read()

# Parse the HTML
soup = BeautifulSoup(html_content, 'html.parser')

# Get all the message divs
roll_divs = soup.select('div.message')
print("Loaded")

div_count = 0
saved_count = 0
last_player_name = ""

processed_rolls = []

def general_roll(roll_div):
    dice_rolled = roll_div.findAll('span', class_='inlinerollresult')

    rolls = []

    for roll in dice_rolled:
        roll_split = roll.get('title').split('=')
        roll_split[0] = roll_split[0].replace("Rolling ", "")
        roll_split[0] = roll_split[0].replace("rolling ", "")

        dice_actually_rolled = roll_split[0]
        actual_result = roll_split[1:]

        dice_actually_rolled = dice_actually_rolled.split('+')[0]
        dice_actually_rolled = dice_actually_rolled.split('c')[0]
        dice_actually_rolled = dice_actually_rolled.split('[')[0]

        if('d' not in dice_actually_rolled or '(' in dice_actually_rolled):
            continue
        
        times_rolled = dice_actually_rolled.split('d')[0]
        dice_type = dice_actually_rolled.split('d')[1]

        for single_roll in actual_result:
            #check if the roll contains a number
            if any (char.isdigit() for char in single_roll):
                #extract the number from the roll
                single_roll = re.findall(r'\d+', single_roll)
                rolls.append(Roll(last_player_name, dice_type, single_roll[0]))
    
    return rolls

def roll_result_div(roll_div):
    rolls = []
    dice_rolled = roll_div.find('div', class_='formula').text.strip()
    dice_rolled = dice_rolled.replace("rolling ", "")

    if('d' not in dice_rolled or '(' in dice_rolled):
        return rolls

    times_rolled = dice_rolled.split('d')[0]
    base_dice = dice_rolled.split('d')[1]
    if(times_rolled == ''):
        times_rolled = '1'

    if('+' in base_dice):
        base_dice = base_dice.split('+')[0].strip()
    if(' ' in base_dice):
        base_dice = base_dice.split(' ')[0].strip()

    try:
        int(base_dice)
    except ValueError:
        return rolls

    result_divs = [result.text.strip() for result in roll_div.findAll('div', class_='didroll')]

    for result in result_divs:
        rolls.append(Roll(last_player_name, base_dice, result))
    
    return rolls

def save_roll(roll):
    cursor.execute('''
        INSERT INTO rolls (player_name, dice, result)
        VALUES (?, ?, ?)
    ''', (roll.player_name, roll.base_dice, roll.roll_result))


for roll_div in roll_divs:
    div_count += 1
    try:
        # Extract player name
        player_name = roll_div.find('span', class_='by')
        if player_name is not None:
            last_player_name = player_name.text.strip().replace(":", "")

        if roll_div.get('class')[1] == 'rollresult':
            rolls = roll_result_div(roll_div)
            for roll in rolls:
                save_roll(roll)
            saved_count += len(rolls)

        elif roll_div.get('class')[1] == 'general':
            rolls = general_roll(roll_div)
            for roll in rolls:
                save_roll(roll)
            saved_count += len(rolls)

    except (AttributeError, ValueError) as e:
        # If any of the expected elements are not found or the result cannot be converted, skip this div
        continue

unpacked_rolls = [single_roll for roll in processed_rolls for single_roll in roll.to_single_rolls()]

conn.commit()
conn.close()

print("All rolls have been saved to the database.")
print('Messages processed:', div_count)
print('Rolls saved:', saved_count)
