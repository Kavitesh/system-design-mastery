"""
Backup Strategies Simulator
============================
Simulates full, incremental, and differential backup strategies.
Compares backup size, creation time, and restore time across strategies
to show why differential backups are the pragmatic middle ground.
"""

import random
import time

# ---------------------------------------------------------------------------
# Data model - simulates a dataset that changes over time
# ---------------------------------------------------------------------------

class Dataset:
    def __init__(self, total_blocks: int, block_size_mb: float):
        self.total_blocks = total_blocks
        self.block_size_mb = block_size_mb
        self.blocks = {i: 0 for i in range(total_blocks)}  # block_id -> version
        self.changed_since_full = set()
        self.changed_since_last = set()

    def simulate_changes(self, change_pct: float):
        num_changes = max(1, int(self.total_blocks * change_pct))
        changed = random.sample(range(self.total_blocks), num_changes)
        for block_id in changed:
            self.blocks[block_id] += 1
            self.changed_since_full.add(block_id)
            self.changed_since_last.add(block_id)
        return changed

    @property
    def total_size_mb(self) -> float:
        return self.total_blocks * self.block_size_mb


# ---------------------------------------------------------------------------
# Backup engines
# ---------------------------------------------------------------------------

class BackupRecord:
    def __init__(self, backup_type: str, blocks_backed_up: int, block_size_mb: float):
        self.backup_type = backup_type
        self.blocks_backed_up = blocks_backed_up
        self.size_mb = blocks_backed_up * block_size_mb
        self.timestamp = time.time()


def full_backup(dataset: Dataset) -> BackupRecord:
    record = BackupRecord("full", dataset.total_blocks, dataset.block_size_mb)
    dataset.changed_since_full.clear()
    dataset.changed_since_last.clear()
    return record


def incremental_backup(dataset: Dataset) -> BackupRecord:
    blocks = len(dataset.changed_since_last)
    record = BackupRecord("incremental", blocks, dataset.block_size_mb)
    dataset.changed_since_last.clear()
    return record


def differential_backup(dataset: Dataset) -> BackupRecord:
    blocks = len(dataset.changed_since_full)
    record = BackupRecord("differential", blocks, dataset.block_size_mb)
    dataset.changed_since_last.clear()
    return record


# ---------------------------------------------------------------------------
# Restore calculators
# ---------------------------------------------------------------------------

def restore_chain_size(backups: list[BackupRecord]) -> float:
    return sum(b.size_mb for b in backups)


def calculate_restore_requirements(strategy: str, history: list[BackupRecord]):
    if strategy == "full":
        return [history[-1]], history[-1].size_mb

    if strategy == "incremental":
        chain = [history[0]]  # full backup
        for b in history[1:]:
            chain.append(b)
        return chain, restore_chain_size(chain)

    if strategy == "differential":
        full = history[0]
        latest_diff = history[-1]
        chain = [full, latest_diff]
        return chain, restore_chain_size(chain)

    return [], 0.0


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

def run_simulation(total_blocks=1000, block_size_mb=1.0, num_days=7, daily_change_pct=0.10):
    print(f"Dataset: {total_blocks} blocks x {block_size_mb} MB = {total_blocks * block_size_mb:.0f} MB total")
    print(f"Simulating {num_days} days with ~{daily_change_pct*100:.0f}% daily change rate")
    print()

    strategies = {
        "Full Daily": [],
        "Full + Incremental": [],
        "Full + Differential": [],
    }

    datasets = {name: Dataset(total_blocks, block_size_mb) for name in strategies}

    for day in range(num_days):
        for name, ds in datasets.items():
            ds.simulate_changes(daily_change_pct)

        # Full daily - full backup every day
        strategies["Full Daily"].append(full_backup(datasets["Full Daily"]))

        # Full + Incremental - full on day 0, incremental after
        if day == 0:
            strategies["Full + Incremental"].append(full_backup(datasets["Full + Incremental"]))
        else:
            strategies["Full + Incremental"].append(incremental_backup(datasets["Full + Incremental"]))

        # Full + Differential - full on day 0, differential after
        if day == 0:
            strategies["Full + Differential"].append(full_backup(datasets["Full + Differential"]))
        else:
            strategies["Full + Differential"].append(differential_backup(datasets["Full + Differential"]))

    # Results
    print("=" * 72)
    print(f"{'Strategy':<25} {'Total Backup Size':>18} {'Day 7 Backup':>14} {'Restore Size':>14}")
    print("=" * 72)

    for name, history in strategies.items():
        total_backup_size = sum(b.size_mb for b in history)
        last_backup_size = history[-1].size_mb
        _, restore_size = calculate_restore_requirements(
            name.split()[-1].lower(), history
        )
        print(f"{name:<25} {total_backup_size:>14.0f} MB {last_backup_size:>10.0f} MB {restore_size:>10.0f} MB")

    print()
    print("--- Day-by-day backup sizes (MB) ---")
    print(f"{'Day':<6}", end="")
    for name in strategies:
        print(f"{name:>25}", end="")
    print()
    print("-" * 81)

    for day in range(num_days):
        print(f"{day+1:<6}", end="")
        for name in strategies:
            size = strategies[name][day].size_mb
            print(f"{size:>25.0f}", end="")
        print()

    print()
    print("--- Restore requirements ---")
    for name, history in strategies.items():
        strategy_key = name.split()[-1].lower()
        chain, total = calculate_restore_requirements(strategy_key, history)
        types = [b.backup_type for b in chain]
        print(f"{name:<25} -> Restore chain: {len(chain)} backup(s) ({', '.join(types)}), {total:.0f} MB total")

    print()
    print("Takeaway: Incremental saves the most storage but needs the longest")
    print("restore chain. Differential is the practical middle ground - fast")
    print("restores with moderate storage cost.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    random.seed(42)
    print("Backup Strategies Simulator")
    print()
    run_simulation(total_blocks=1000, block_size_mb=1.0, num_days=7, daily_change_pct=0.10)
