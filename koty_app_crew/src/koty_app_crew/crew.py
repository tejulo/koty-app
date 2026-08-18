"""Crew secuencial completo para implementar y archivar un cambio OpenSpec."""

import os

from crewai import Agent, Crew, LLM, Process, Task
from crewai.project import CrewBase, agent, crew, task
from .tools.custom_tool import buscar_tarea_linear, ejecutar_openspec, escribir_archivo_raiz
from crewai_tools import FileReadTool

herramienta_leer = FileReadTool()

DEFAULT_ZEN_BASE_URL = "https://opencode.ai/zen/go/v1"

def _zen_llm(nombre_variable_modelo: str) -> LLM:
    model = os.environ.get(nombre_variable_modelo)
    api_key = os.environ.get("OPENCODE_API_KEY")
    if not model or not api_key:
        raise ValueError(f"{nombre_variable_modelo} y OPENCODE_API_KEY son requeridos")

    return LLM(
        model=model,
        base_url=os.environ.get("ZEN_BASE_URL", DEFAULT_ZEN_BASE_URL),
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
            llm=_zen_llm("ZEN_MANAGER_MODEL"),
            verbose=True,
            allow_delegation=False,
            tools=[buscar_tarea_linear]
        )

    @agent
    def arquitect(self) -> Agent:
        return Agent(
            config=self.agents_config['arquitect'],
            verbose=True,
            allow_delegation=False,
            llm=_zen_llm("ZEN_MANAGER_MODEL"),
            # Ahora el arquitecto puede leer el contexto y escribir las especificaciones
            tools=[herramienta_leer, ejecutar_openspec, escribir_archivo_raiz]
        )

    @agent
    def programer(self) -> Agent:
        return Agent(
            config=self.agents_config["programer"],
            llm=_zen_llm("ZEN_CODER_MODEL"),
            verbose=True,
            allow_delegation=False,
            tools=[herramienta_leer, escribir_archivo_raiz]
        )

    @agent
    def reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["reviewer"],
            llm=_zen_llm("ZEN_REVIEWER_MODEL"),
            verbose=True,
            allow_delegation=False,
            tools=[herramienta_leer, ejecutar_openspec]
        )

    @task
    def analysis_task(self) -> Task:
        return Task(config=self.tasks_config['analysis_task'])

    @task
    def architecture_task(self) -> Task:
        return Task(config=self.tasks_config['architecture_task'])

    @task
    def coding_task(self) -> Task:
        return Task(config=self.tasks_config['coding_task'])

    @task
    def review_task(self) -> Task:
        return Task(config=self.tasks_config['review_task'])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[self.analyst(), self.arquitect(), self.programer(), self.reviewer()],
            tasks=[self.analysis_task(), self.architecture_task(), self.coding_task(), self.review_task()],
            process=Process.sequential, 
            verbose=True,
        )
