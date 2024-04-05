import turtle

def execute_turtle_command(command_words):
    action = command_words[0]
    if action == "Avance":
        turtle.forward(int(command_words[1]))
    elif action == "Recule":
        turtle.backward(int(command_words[1]))
    elif action == "Tourne":
        direction = command_words[1]
        angle = int(command_words[3])
        if direction == "droite":
            turtle.right(angle)
        elif direction == "gauche":
            turtle.left(angle)

with open("./turtle", "r") as file:
    for line in file:
        command_words = line.strip().split()
        if command_words:  # Check for non-empty lines
            execute_turtle_command(command_words)

turtle.done()
