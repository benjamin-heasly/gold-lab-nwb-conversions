from proceed.cli import main

# We got these Python variabls from somehere.
# We'd like to pass them in to a Proceed pipeline run.
first_thing = "cool"
second_thing = "script"

# Instead of one command line on the shell, with parts separated by spaces,
# we pass the command as a Python list of string elements.
# Some of the command parts have internal structure, like "name=value" assignments.
# Python "f-strings" are a handy way to build these, like f"name={value}".
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
