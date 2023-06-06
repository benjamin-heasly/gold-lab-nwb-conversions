How am I installing this for dev?

I'm using the same "gold_nwb" environment created from the `environment.yml` at the top of this repo.

```
conda activate gold_nwb
```

I'm also installing the [hatch](https://github.com/pypa/hatch) command with developer tooling.
You probably want to install hatch if you're doing dev, probably not otherwise.

```
pipx install hatch
```

When doing dev, I'm running the tests like this:

```
hatch run test:cov
```
