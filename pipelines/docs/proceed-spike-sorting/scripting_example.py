from proceed.cli import main

# We got these Python variables from somehere.
# We'd like to pass them in to a Proceed pipeline run.
first_thing = "cool"
second_thing = "script"

# On the shell we pass one long command string with parts separated by spaces.
# Here, a list of strings, where each list element corresponds to a command part.
# Some of Proceed's command parts have internal structure, like "name=value" args assignments.
# We can build each of these using Python "f-string" formatting, like f"name={value}".
command = [
    "run",
    "scripting-example.yaml",
    "--args",
    f"first_thing={first_thing}",
    f"second_thing={second_thing}"
]

print("I'm running Proceed!")
exit_code = main(command)
print(f"Proceed exited with code {exit_code}.")
