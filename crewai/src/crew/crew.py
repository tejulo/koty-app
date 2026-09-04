import os
from typing import Literal

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
    PlanArtifactUnit,
    PlanOutline,
    ReviewVerdict,
    TesterResult,
    TicketContract,
)
from .tools.custom_tool import (
    buscar_tarea_linear,
    ejecutar_playwright,
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
    max_tokens_env: str,
    default_max_tokens: int,
    reasoning_effort: Literal["none", "low", "medium", "high"] | None = None,
    max_retries: int | None = None,
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

    options = {
        "model": model,
        "base_url": os.environ.get(
            "ZEN_BASE_URL",
            DEFAULT_ZEN_BASE_URL,
        ),
        "api_key": api_key,
        "temperature": 0.2,
        "reasoning_effort": reasoning_effort,
        "max_tokens": int(
            os.environ.get(
                max_tokens_env,
                default_max_tokens,
            )
        ),
    }
    if max_retries is not None:
        options["max_retries"] = max_retries
    return LLM(**options)


@CrewBase
class KotyAppCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["analyst"],
            llm=_zen_llm(
                "ZEN_ANALYST_MODEL",
                "ZEN_ANALYST_MAX_TOKENS",
                2000,
            ),
            tools=[
                buscar_tarea_linear,
            ],
            verbose=VERBOSE,
            allow_delegation=False,
            respect_context_window=True,
            max_iter=4,
            tool_failure_policy=(
                ToolFailurePolicy.RAISE
            ),
        )

    def _architect(self, max_tokens_env: str, default_max_tokens: int) -> Agent:
        return Agent(
            config=self.agents_config["arquitect"],
            llm=_zen_llm(
                "ZEN_ARCHITECT_MODEL",
                max_tokens_env,
                default_max_tokens,
                reasoning_effort="low",
                max_retries=0,
            ),
            tools=[],
            verbose=VERBOSE,
            allow_delegation=False,
            respect_context_window=False,
            max_iter=1,
            max_retry_limit=0,
        )

    @agent
    def programer(self) -> Agent:
        return Agent(
            config=self.agents_config["programer"],
            llm=_zen_llm(
                "ZEN_CODER_MODEL",
                "ZEN_CODER_MAX_TOKENS",
                2500,
            ),
            tools=[
                leer_archivo_raiz,
                listar_archivos_raiz,
                escribir_archivo_raiz,
            ],
            verbose=VERBOSE,
            allow_delegation=False,
            respect_context_window=True,
            max_iter=20,
        )

    @agent
    def tester(self) -> Agent:
        return Agent(
            config=self.agents_config["tester"],
            llm=_zen_llm(
                "ZEN_TESTER_MODEL",
                "ZEN_TESTER_MAX_TOKENS",
                600,
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
            max_iter=8,
        )

    @agent
    def reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["reviewer"],
            llm=_zen_llm(
                "ZEN_REVIEWER_MODEL",
                "ZEN_REVIEWER_MAX_TOKENS",
                800,
            ),
            tools=[
                leer_archivo_raiz,
                listar_archivos_raiz,
            ],
            verbose=VERBOSE,
            allow_delegation=False,
            respect_context_window=True,
            max_iter=8,
        )

    @task
    def analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config[
                "analysis_task"
            ],
            output_pydantic=TicketContract,
        )

    def architect_outline_task(self) -> Task:
        agent = self._architect("ZEN_ARCHITECT_OUTLINE_MAX_TOKENS", 4000)
        return Task(
            name="architect_outline_task",
            config=self.tasks_config["architect_outline_task"],
            agent=agent,
            output_pydantic=PlanOutline,
        )

    def architect_artifact_task(self, *, retry: bool = False) -> Task:
        max_tokens_env = (
            "ZEN_ARCHITECT_RETRY_MAX_TOKENS"
            if retry
            else "ZEN_ARCHITECT_ARTIFACT_MAX_TOKENS"
        )
        default_max_tokens = 16000 if retry else 8000
        agent = self._architect(max_tokens_env, default_max_tokens)
        return Task(
            name="architect_artifact_task",
            config=self.tasks_config["architect_artifact_task"],
            agent=agent,
            output_pydantic=PlanArtifactUnit,
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
            ],
            output_pydantic=ReviewVerdict,
        )

    @crew
    def analyst_crew(self) -> Crew:
        return self._crew(
            [self.analyst()],
            [self.analysis_task()],
        )

    def architect_outline_crew(self) -> Crew:
        task = self.architect_outline_task()
        return self._crew(
            [task.agent],
            [task],
        )

    def architect_artifact_crew(self, *, retry: bool = False) -> Crew:
        task = self.architect_artifact_task(retry=retry)
        return self._crew(
            [task.agent],
            [task],
        )

    @crew
    def programmer_crew(self) -> Crew:
        return self._crew(
            [self.programer()],
            [self.coding_task()],
        )

    @crew
    def tester_crew(self) -> Crew:
        return self._crew(
            [self.tester()],
            [self.testing_task()],
        )

    @crew
    def reviewer_crew(self) -> Crew:
        return self._crew(
            [self.reviewer()],
            [self.review_task()],
        )

    @crew
    def delivery_crew(self) -> Crew:
        return self._crew(
            [self.programer(), self.tester(), self.reviewer()],
            [self.coding_task(), self.testing_task(), self.review_task()],
        )

    def _crew(self, agents, tasks) -> Crew:
        options = {
            "agents": agents,
            "tasks": tasks,
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
