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
cd pyramid
hatch run test:cov
```

Hatch is smart enough to install pytest automatically in the tests environment it creates.
The reason I also install pytest locally is so that my IDE recognizes pytest for syntax highlighting, etc.

Once, on my 2021 M1 iMac with Ventura 31.4, running `hatch run test:cov` failed.  It was not installing the pyramid project itself into the test environment.  So tests all failed with messages like `ModuleNotFoundError: no module named pyramid`.  Why did this happen?  I don't know.  But asking hatch to recreate the environments helped.
```
hatch env --help
hatch env prune
hatch run test:cov
```
