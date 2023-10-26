# Cloud Native Backend
## Setup
1. Python environment
   ```shell
   pip install poetry
   poetry install
   cp .env.example .env
   ```
   and paste environment variables
2. Run backend service
    ```shell
    make run
    ```

3. Backend openapi documents should be accessed through http://localhost:8000/docs