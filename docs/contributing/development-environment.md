# Set up a development environment

The package is developed with [uv](https://docs.astral.sh/uv/), which installs the Python version
and every dependency the project needs. This page takes you from a clone of the repository to the
example project running on your machine.

## Install the project

1. Clone the repository.

   ```console
   $ git clone https://github.com/FAIR-DM/django-partial-dates.git
   $ cd django-partial-dates
   ```

2. Install the dependencies, including the development tools.

   ```console
   $ uv sync
   ```

3. Install the hooks, so that the linters run on every commit.

   ```console
   $ uv run pre-commit install
   ```

## Run the example project

The repository holds a small project, in `example/`, with a list of samples, a form to enter one and the admin.

1. Create the database and fill it.

   ```console
   $ uv run python example/manage.py migrate
   $ uv run python example/manage.py seed
   ```

2. Start the server.

   ```console
   $ uv run python example/manage.py runserver 8033
   ```

3. Open `http://localhost:8033/`.
