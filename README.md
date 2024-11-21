# Django Filtering

A library for filtering Django Models.

The original usecase for this project required the following:

- provides a means of allowing users to filter modeled data
- provides the ability to `AND`, `OR` and `NOT` filters (i.e. operators)
- provides the ability to group filters by operator
- serializes, validates, etc.


## Development

This project is very much a work-in-progress. All APIs are completely unstable.

### Testing

Note, I'm testing within a docker container, because I never run anything locally.
For the moment the container is simply run with:

    docker run --rm --name django-filtering --workdir /code -v $PWD:/code -d python:3.12 sleep infinity

Then I execute commands on the shell within it:

    docker exec -it django-filtering bash


## License

GPL v3 (see `LICENSE` file)


## Copyright

© 2024 The Shadowserver Foundation
