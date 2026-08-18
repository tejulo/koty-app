"""Crew jerarquico para implementar y revisar un cambio OpenSpec."""

import os

from crewai import Agent, Crew, LLM, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task
from .tools.custom_tool import buscar_tarea_linear, ejecutar_openspec
from crewai_tools import FileReadTool, FileWriterTool

herramienta_leer = FileReadTool()
herramienta_escribir = FileWriterTool()

DEFAULT_ZEN_BASE_URL = "https://opencode.ai/zen/go/v1"

def _zen_llm(temperature: float, nombre_variable_modelo: str) -> LLM:
    model = os.environ.get(nombre_variable_modelo)
    api_key = os.environ.get("OPENCODE_API_KEY")
    if not model or not api_key:
        raise ValueError(f"{nombre_variable_modelo} and OPENCODE_API_KEY are required")

    return LLM(
        model=model,
        base_url=os.environ.get("ZEN_BASE_URL", DEFAULT_ZEN_BASE_URL),
        api_key=api_key,
        temperature=temperature,
    )

@CrewBase
class KotyAppCrew:
    """Coordinates implementation and review of an OpenSpec change."""

    agents: list[BaseAgent]
    tasks: list[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def manager(self) -> Agent:
        return Agent(
            config=self.agents_config["manager"],  # type: ignore[index]
            llm=_zen_llm(temperature=0.2, nombre_variable_modelo="ZEN_MANAGER_MODEL"),
            verbose=True,
            allow_delegation=True
        )

    @agent
    def analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["analyst"],
            llm=_zen_llm(temperature=0.2, nombre_variable_modelo="ZEN_MANAGER_MODEL"), # Usamos el mismo modelo para simplificar
            verbose=True,
            allow_delegation=False,
            tools=[buscar_tarea_linear] # El analista tiene la herramienta
        )

    @agent
    def arquitect(self) -> Agent:
        return Agent(
            config=self.agents_config['arquitect'],
            verbose=True,
            allow_delegation=False,
            llm=_zen_llm(temperature=0.2, nombre_variable_modelo="ZEN_MANAGER_MODEL"),
            tools=[ejecutar_openspec]
        )

    @agent
    def programer(self) -> Agent:
        return Agent(
            config=self.agents_config["programer"],  # type: ignore[index]
            llm=_zen_llm(temperature=0.3, nombre_variable_modelo="ZEN_CODER_MODEL"),
            verbose=True,
            allow_delegation=False,
            tools=[herramienta_leer, herramienta_escribir]
        )

    @agent
    def reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["reviewer"],  # type: ignore[index]
            llm=_zen_llm(temperature=0.1, nombre_variable_modelo="ZEN_REVIEWER_MODEL"),
            verbose=True,
            allow_delegation=False,
            tools=[herramienta_leer]
        )

    @task
    def analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['analysis_task'],
        )

    @task
    def architecture_task(self) -> Task:
        return Task(
            config=self.tasks_config['architecture_task'],
        )

    @task
    def coding_task(self) -> Task:
        return Task(
            config=self.tasks_config['coding_task'],
        )

    @task
    def review_task(self) -> Task:
        return Task(
            config=self.tasks_config['review_task'],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents, # Ahora solo tiene al arquitecto, programador y revisor
            tasks=self.tasks,
            manager_agent=self.manager(), # 2. Asignamos al jefe explícitamente
            process=Process.hierarchical, # 3. Activamos el modo orquestador
            verbose=True,
        )
