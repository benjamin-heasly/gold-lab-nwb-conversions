How am I installing this for dev?

I'm using the same "gold_nwb" environment created from the `environment.yml` at the top of this repo.

```
conda activate gold_nwb
```

I'm also installing the [hatch](https://github.com/pypa/hatch) command with developer tooling
and [pytest](https://docs.pytest.org/en/7.1.x/getting-started.html) for writing tests locally.
You probably want to install both of these if you're doing dev, probably not otherwise.

```
pipx install hatch
pip install pytest
```

When doing dev, I'm running the tests like this:

```
hatch run test:cov
```

Hatch is smart enough to install pytest automatically in the tests environment it creates.
The reason I also install pytest locally is so that my IDE recognizes pytest for syntax highlighting, etc.
