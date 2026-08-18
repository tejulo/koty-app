"""
Crew secuencial para automatizar:

Linear
    -> análisis
    -> OpenSpec
    -> implementación
    -> verificación
    -> archive
"""

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

from .tools.custom_tool import (
    buscar_tarea_linear,
    ejecutar_openspec,
    ejecutar_verificacion,
    escribir_archivo_raiz,
    leer_archivo_raiz,
    listar_archivos_raiz,
)


DEFAULT_ZEN_BASE_URL = (
    "https://opencode.ai/zen/go/v1"
)


def _zen_llm(
    nombre_variable_modelo: str,
) -> LLM:
    """
    Construye el LLM utilizado por cada agente.
    """

    model = os.environ.get(
        nombre_variable_modelo
    )

    api_key = os.environ.get(
        "OPENCODE_API_KEY"
    )

    if not model:
        raise ValueError(
            "Falta la variable de entorno "
            f"{nombre_variable_modelo}"
        )

    if not api_key:
        raise ValueError(
            "Falta la variable de entorno "
            "OPENCODE_API_KEY"
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
    """
    Crew secuencial para procesar un ticket
    desde Linear hasta OpenSpec archive.
    """

    agents_config = (
        "config/agents.yaml"
    )

    tasks_config = (
        "config/tasks.yaml"
    )

    # ========================================================
    # Agents
    # ========================================================

    @agent
    def analyst(self) -> Agent:
        return Agent(
            config=self.agents_config[
                "analyst"
            ],
            llm=_zen_llm(
                "ZEN_ANALYST_MODEL"
            ),
            verbose=True,
            allow_delegation=False,

            # CrewAI resumirá el historial si se
            # aproxima al límite del modelo.
            respect_context_window=True,

            max_iter=10,

            tools=[
                buscar_tarea_linear,
            ],
        )

    @agent
    def arquitect(self) -> Agent:
        return Agent(
            config=self.agents_config[
                "arquitect"
            ],
            llm=_zen_llm(
                "ZEN_ARCHITECT_MODEL"
            ),
            verbose=True,
            allow_delegation=False,
            respect_context_window=True,

            # Evitar loops excesivos que hagan crecer
            # indefinidamente el contexto.
            max_iter=30,

            tools=[
                leer_archivo_raiz,
                listar_archivos_raiz,
                ejecutar_openspec,
                escribir_archivo_raiz,
            ],
        )

    @agent
    def programer(self) -> Agent:
        return Agent(
            config=self.agents_config[
                "programer"
            ],
            llm=_zen_llm(
                "ZEN_CODER_MODEL"
            ),
            verbose=True,
            allow_delegation=False,
            respect_context_window=True,

            max_iter=60,

            tools=[
                leer_archivo_raiz,
                listar_archivos_raiz,
                escribir_archivo_raiz,
                ejecutar_verificacion,
            ],
        )

    @agent
    def reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config[
                "reviewer"
            ],
            llm=_zen_llm(
                "ZEN_REVIEWER_MODEL"
            ),
            verbose=True,
            allow_delegation=False,
            respect_context_window=True,

            max_iter=30,

            tools=[
                leer_archivo_raiz,
                listar_archivos_raiz,
                ejecutar_openspec,
                ejecutar_verificacion,
            ],
        )

    # ========================================================
    # Tasks
    # ========================================================

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
    def review_task(self) -> Task:
        return Task(
            config=self.tasks_config[
                "review_task"
            ]
        )

    # ========================================================
    # Crew
    # ========================================================

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[
                self.analyst(),
                self.arquitect(),
                self.programer(),
                self.reviewer(),
            ],

            tasks=[
                self.analysis_task(),
                self.architecture_task(),
                self.coding_task(),
                self.review_task(),
            ],

            process=Process.sequential,

            verbose=True,

            # Desactivar explícitamente tracing.
            tracing=False,
        )
