"""
DAG-Based Pipeline Executor
============================
Builds a directed acyclic graph of pipeline tasks, resolves dependencies
using topological sort, and executes tasks in parallel where possible.
"""

import time
import random
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum


# ---------------------------------------------------------------------------
#   Task definitions
# ---------------------------------------------------------------------------

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    name: str
    duration: float  # simulated seconds
    dependencies: list = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: dict = None
    fail_rate: float = 0.0  # probability of failure


# ---------------------------------------------------------------------------
#   DAG builder and validator
# ---------------------------------------------------------------------------

class DAG:
    def __init__(self):
        self.tasks = {}
        self.graph = defaultdict(set)
        self.reverse_graph = defaultdict(set)

    def add_task(self, task):
        self.tasks[task.name] = task
        for dep in task.dependencies:
            self.graph[dep].add(task.name)
            self.reverse_graph[task.name].add(dep)

    def validate(self):
        """Check for cycles using DFS."""
        visited = set()
        in_stack = set()

        def dfs(node):
            visited.add(node)
            in_stack.add(node)
            for neighbor in self.graph[node]:
                if neighbor in in_stack:
                    return False, f"Cycle detected: {node} -> {neighbor}"
                if neighbor not in visited:
                    ok, msg = dfs(neighbor)
                    if not ok:
                        return False, msg
            in_stack.remove(node)
            return True, ""

        for task_name in self.tasks:
            if task_name not in visited:
                ok, msg = dfs(task_name)
                if not ok:
                    return False, msg

        # Check for missing dependencies
        for name, task in self.tasks.items():
            for dep in task.dependencies:
                if dep not in self.tasks:
                    return False, f"Task '{name}' depends on unknown task '{dep}'"

        return True, "DAG is valid"

    def topological_sort(self):
        """Return tasks in execution order using Kahn's algorithm."""
        in_degree = {name: len(self.reverse_graph[name]) for name in self.tasks}
        queue = deque([n for n, d in in_degree.items() if d == 0])
        order = []

        while queue:
            node = queue.popleft()
            order.append(node)
            for neighbor in self.graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(self.tasks):
            raise ValueError("Cycle detected - topological sort impossible")
        return order

    def get_ready_tasks(self, completed):
        """Return tasks whose dependencies are all satisfied."""
        ready = []
        for name, task in self.tasks.items():
            if task.status != TaskStatus.PENDING:
                continue
            if all(d in completed for d in task.dependencies):
                ready.append(name)
        return ready


# ---------------------------------------------------------------------------
#   Executor
# ---------------------------------------------------------------------------

def execute_task(task):
    """Simulate running a pipeline task."""
    task.status = TaskStatus.RUNNING
    time.sleep(task.duration)

    if random.random() < task.fail_rate:
        task.status = TaskStatus.FAILED
        task.result = {"error": "simulated failure"}
        return task

    task.status = TaskStatus.COMPLETED
    task.result = {
        "rows_processed": random.randint(1000, 50000),
        "duration_actual": task.duration,
    }
    return task


def run_dag(dag, max_workers=4):
    """Execute all tasks in the DAG, respecting dependencies and parallelism."""
    valid, msg = dag.validate()
    if not valid:
        print(f"  DAG validation failed: {msg}")
        return False

    topo_order = dag.topological_sort()
    print(f"  Execution order: {' -> '.join(topo_order)}")

    completed = set()
    failed = set()
    start_time = time.perf_counter()

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        running_futures = {}

        while len(completed) + len(failed) < len(dag.tasks):
            ready = dag.get_ready_tasks(completed)
            for task_name in ready:
                if task_name not in running_futures:
                    task = dag.tasks[task_name]
                    task.status = TaskStatus.RUNNING
                    future = pool.submit(execute_task, task)
                    running_futures[task_name] = future
                    print(f"  [{_elapsed(start_time)}] STARTED:   {task_name}")

            done_names = []
            for name, future in running_futures.items():
                if future.done():
                    done_names.append(name)
                    result_task = future.result()
                    if result_task.status == TaskStatus.COMPLETED:
                        completed.add(name)
                        rows = result_task.result["rows_processed"]
                        print(f"  [{_elapsed(start_time)}] COMPLETED: {name} "
                              f"({rows:,} rows)")
                    else:
                        failed.add(name)
                        print(f"  [{_elapsed(start_time)}] FAILED:    {name}")

            for name in done_names:
                del running_futures[name]

            if running_futures:
                time.sleep(0.05)

    total_time = time.perf_counter() - start_time
    return completed, failed, total_time


def _elapsed(start):
    return f"{time.perf_counter() - start:5.2f}s"


# ---------------------------------------------------------------------------
#   Demo pipeline
# ---------------------------------------------------------------------------

def build_demo_pipeline():
    """
    Build a realistic ETL pipeline DAG:

    extract_users -----> clean_users ------\
                                            --> join_data --> aggregate --> load_warehouse
    extract_orders --> clean_orders -------/
                   \
                    --> compute_metrics --> load_dashboard
    """
    dag = DAG()

    dag.add_task(Task("extract_users", duration=0.3))
    dag.add_task(Task("extract_orders", duration=0.4))

    dag.add_task(Task("clean_users", duration=0.2, dependencies=["extract_users"]))
    dag.add_task(Task("clean_orders", duration=0.3, dependencies=["extract_orders"]))

    dag.add_task(Task(
        "join_data", duration=0.5,
        dependencies=["clean_users", "clean_orders"]
    ))
    dag.add_task(Task(
        "compute_metrics", duration=0.2,
        dependencies=["extract_orders"]
    ))

    dag.add_task(Task("aggregate", duration=0.3, dependencies=["join_data"]))
    dag.add_task(Task(
        "load_warehouse", duration=0.2, dependencies=["aggregate"]
    ))
    dag.add_task(Task(
        "load_dashboard", duration=0.15, dependencies=["compute_metrics"]
    ))

    return dag


def main():
    print("DAG Pipeline Executor Demo")

    random.seed(42)
    dag = build_demo_pipeline()

    valid, msg = dag.validate()
    print(f"\n{'='*60}")
    print(f"  Pipeline DAG - {len(dag.tasks)} tasks")
    print(f"{'='*60}")
    print(f"  Validation: {msg}")

    print(f"\n  Task dependencies:")
    for name, task in sorted(dag.tasks.items()):
        deps = task.dependencies if task.dependencies else ["(none)"]
        print(f"    {name:<20} depends on: {', '.join(deps)}")

    print(f"\n{'='*60}")
    print(f"  Executing pipeline (max 4 parallel workers)")
    print(f"{'='*60}")

    completed, failed, total = run_dag(dag, max_workers=4)

    print(f"\n{'='*60}")
    print(f"  Pipeline Results")
    print(f"{'='*60}")
    print(f"  Total wall time:  {total:.2f}s")
    serial_time = sum(t.duration for t in dag.tasks.values())
    print(f"  Serial time:      {serial_time:.2f}s")
    speedup = serial_time / total if total > 0 else 0
    print(f"  Parallel speedup: {speedup:.1f}x")
    print(f"  Completed:        {len(completed)}/{len(dag.tasks)}")
    print(f"  Failed:           {len(failed)}/{len(dag.tasks)}")

    if completed:
        print(f"\n  Execution summary:")
        for name in dag.topological_sort():
            task = dag.tasks[name]
            symbol = "+" if task.status == TaskStatus.COMPLETED else "x"
            rows = task.result.get("rows_processed", 0) if task.result else 0
            print(f"    [{symbol}] {name:<20} {rows:>8,} rows  ({task.duration:.1f}s)")


if __name__ == "__main__":
    main()
