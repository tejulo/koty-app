import os

from crewai import (
    Agent,
    Crew,
    LLM,
    Process,
    Task,
)
from crewai.project import (
    CrewBase,
    agent,
    crew,
    task,
)
from crewai.tools.tool_failure import (
    ToolFailurePolicy,
)

from .models import (
    TesterResult,
)
from .tools.custom_tool import (
    buscar_tarea_linear,
    ejecutar_openspec,
    ejecutar_playwright,
    ejecutar_verificacion,
    escribir_archivo_raiz,
    gestionar_entorno_local,
    leer_archivo_raiz,
    listar_archivos_raiz,
)


DEFAULT_ZEN_BASE_URL = (
    "https://opencode.ai/zen/go/v1"
)

VERBOSE = (
    os.environ.get(
        "CREWAI_VERBOSE",
        "false",
    ).lower()
    == "true"
)


def _zen_llm(
    model_env: str,
) -> LLM:
    model = os.environ.get(model_env)
    api_key = os.environ.get(
        "OPENCODE_API_KEY"
    )

    if not model:
        raise ValueError(
            f"Falta {model_env}"
        )

    if not api_key:
        raise ValueError(
            "Falta OPENCODE_API_KEY"
        )

    return LLM(
        model=model,
        base_url=os.environ.get(
            "ZEN_BASE_URL",
            DEFAULT_ZEN_BASE_URL,
        ),
        api_key=api_key,
        temperature=0.2,
    )


@CrewBase
class KotyAppCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["analyst"],
            llm=_zen_llm(
                "ZEN_ANALYST_MODEL"
            ),
            tools=[
                buscar_tarea_linear,
            ],
            verbose=VERBOSE,
            allow_delegation=False,
            respect_context_window=True,
            max_iter=10,
            tool_failure_policy=(
                ToolFailurePolicy.RAISE
            ),
        )

    @agent
    def arquitect(self) -> Agent:
        return Agent(
            config=self.agents_config["arquitect"],
            llm=_zen_llm(
                "ZEN_ARCHITECT_MODEL"
            ),
            tools=[
                leer_archivo_raiz,
                listar_archivos_raiz,
                escribir_archivo_raiz,
                ejecutar_openspec,
            ],
            verbose=VERBOSE,
            allow_delegation=False,
            respect_context_window=True,
            max_iter=30,
        )

    @agent
    def programer(self) -> Agent:
        return Agent(
            config=self.agents_config["programer"],
            llm=_zen_llm(
                "ZEN_CODER_MODEL"
            ),
            tools=[
                leer_archivo_raiz,
                listar_archivos_raiz,
                escribir_archivo_raiz,
                ejecutar_verificacion,
            ],
            verbose=VERBOSE,
            allow_delegation=False,
            respect_context_window=True,
            max_iter=60,
        )

    @agent
    def tester(self) -> Agent:
        return Agent(
            config=self.agents_config["tester"],
            llm=_zen_llm(
                "ZEN_TESTER_MODEL"
            ),
            tools=[
                leer_archivo_raiz,
                listar_archivos_raiz,
                gestionar_entorno_local,
                ejecutar_playwright,
            ],
            verbose=VERBOSE,
            allow_delegation=False,
            respect_context_window=True,
            max_iter=30,
        )

    @agent
    def reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["reviewer"],
            llm=_zen_llm(
                "ZEN_REVIEWER_MODEL"
            ),
            tools=[
                leer_archivo_raiz,
                listar_archivos_raiz,
                ejecutar_verificacion,
                ejecutar_openspec,
            ],
            verbose=VERBOSE,
            allow_delegation=False,
            respect_context_window=True,
            max_iter=30,
        )

    @task
    def analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config[
                "analysis_task"
            ]
        )

    @task
    def architecture_task(self) -> Task:
        return Task(
            config=self.tasks_config[
                "architecture_task"
            ]
        )

    @task
    def coding_task(self) -> Task:
        return Task(
            config=self.tasks_config[
                "coding_task"
            ]
        )

    @task
    def testing_task(self) -> Task:
        return Task(
            config=self.tasks_config[
                "testing_task"
            ],
            output_pydantic=TesterResult,
        )

    @task
    def review_task(self) -> Task:
        return Task(
            config=self.tasks_config[
                "review_task"
            ]
        )

    @crew
    def crew(self) -> Crew:
        options = {
            "agents": [
                self.analyst(),
                self.arquitect(),
                self.programer(),
                self.tester(),
                self.reviewer(),
            ],
            "tasks": [
                self.analysis_task(),
                self.architecture_task(),
                self.coding_task(),
                self.testing_task(),
                self.review_task(),
            ],
            "process": Process.sequential,
            "verbose": VERBOSE,
            "tracing": False,
        }
        log_file = os.environ.get("CREWAI_OUTPUT_LOG_FILE")

        if log_file:
            options["output_log_file"] = log_file

        return Crew(
            **options,
        )
