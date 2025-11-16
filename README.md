# OpenCFD

OpenCFD is a web-based platform that uses the open-source Foam-Agent framework to run end-to-end CFD simulations from a single text prompt.

A user simply types what they want to simulate (e.g., "Simulate incompressible flow over a circular cylinder... using gmsh to create the mesh"). Our backend, powered by Foam-Agent, then orchestrates a team of specialized AI agents to handle the entire complex workflow:

1. Architect Agent: First, this agent plans the entire simulation, defining the required directory structure and file dependencies.
2. Meshing Agent: This agent automatically generates the computational mesh. It is incredibly versatile, supporting text-to-mesh generation via the Gmsh library, importing external user-provided meshes, or using OpenFOAM's native tools.
3. Input Writer Agent: This agent generates all the complex OpenFOAM configuration files. Crucially, it writes them in a "dependency-aware sequence" (e.g., system files first, then constant, then 0 files) to ensure consistency and reduce errors.
4. Runner Agent: This agent executes the simulation. For this hackathon, we run it locally, but the framework is designed to automatically generate Slurm scripts and submit jobs to HPC clusters.
5. Reviewer Agent: This is the most critical part. If the simulation fails, the Runner Agent extracts the error logs. The Reviewer Agent then analyzes the error and automatically proposes a fix. The system then re-runs the simulation in an iterative loop until it succeeds.
6. Visualization Agent: Finally, this agent generates plots and visualizations (like velocity fields) from the results, again based on the user's prompt.

---

A Chainlit-based frontend that sends user requirements to a Flask backend, which runs `foambench_main.py` to generate OpenFOAM cases.

---

## Setup: Create & Activate Conda Environment

We use **Conda** to manage dependencies and ensure reproducibility.

### 1. Create the Conda Environment

```bash
conda env create --file environment.yml
```
```bash
conda activate website
```
### 2. Pull Docker Container

A docker image for Foam-Agent https://github.com/csml-rpi/Foam-Agent.
1. To pull the image, do
`docker pull leoyue123/foamagent`
2. Afterwards, do
`docker run -it -e OPENAI_API_KEY=your-key-here -p 7860:7860 --name opencfd leoyue123/foamagent`
to run a container with an interactive terminal.
  1. Set your OpenAI key: `export OPENAI_API_KEY=<your-openai-key>`
3. Start/restart the container by
`docker start -i foamagent`
4. Once the terminal starts, do
`conda init`
to initialize conda for shell interaction.
5. `exit` for the changes to take effect (steps 3 and 4 only need to be done once).
6. Restart the container by
`docker start -i foamagent`
7. Activate the FoamAgent environment:
`conda activate FoamAgent`
8. To run backend: `python adapter.py`

### 3. Set up Chain-lit

To initialize the app:
```bash
chainlit run web.py -w
```
Then go to  `http://localhost:8000/` and type in your user_requirement.