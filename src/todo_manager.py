"""Task management for Enterprise Deep Research logic."""
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Task:
    id: str
    description: str
    status: str = "pending" # pending, completed, canceled
    priority: int = 5
    result: Optional[str] = None

class ResearchTodoManager:
    def __init__(self):
        self.tasks: List[Task] = []

    def add_task(self, description: str, priority: int = 5):
        task_id = str(len(self.tasks) + 1)
        self.tasks.append(Task(id=task_id, description=description, priority=priority))
        return task_id

    def complete_task(self, task_id: str, result: str):
        for t in self.tasks:
            if t.id == task_id:
                t.status = "completed"
                t.result = result
                return
        raise ValueError(f"Task with id {task_id} not found")
    
    def complete_all(self, result: str = "Done"):
        """Mark all pending tasks as complete."""
        for t in self.tasks:
            if t.status == "pending":
                t.status = "completed"
                t.result = result

    def get_next_task(self) -> Optional[Task]:
        pending = [t for t in self.tasks if t.status == "pending"]
        if not pending:
            return None
        # Retorna la tarea pendiente de mayor prioridad
        return sorted(pending, key=lambda x: -x.priority)[0]

    def get_plan_view(self) -> str:
        """Generates the text view for the LLM."""
        view = "## RESEARCH PLAN (TODO LIST)\n"
        
        pending = [t for t in self.tasks if t.status == "pending"]
        if pending:
            view += "### PENDING TASKS:\n"
            for t in sorted(pending, key=lambda x: -x.priority):
                view += f"- [ ] (ID: {t.id}) {t.description} [Priority: {t.priority}]\n"
        else:
            view += "### NO PENDING TASKS (Generate new ones or Answer)\n"

        completed = [t for t in self.tasks if t.status == "completed"]
        if completed:
            view += "\n### COMPLETED:\n"
            for t in completed:
                view += f"- [x] {t.description}\n"
        
        return view
