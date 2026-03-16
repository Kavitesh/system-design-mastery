"""
Amdahl's Law Calculator & Visualizer
=====================================
Shows the theoretical maximum speedup based on
how much of the workload can be parallelized.

Run: python amdahls_law.py
"""


def amdahls_speedup(parallel_fraction: float, num_processors: int) -> float:
    """
    Calculate max speedup using Amdahl's Law.

    Speedup = 1 / ((1 - P) + P/N)
      P = fraction of work that can be parallelized (0 to 1)
      N = number of processors / servers
    """
    serial_fraction = 1 - parallel_fraction
    return 1.0 / (serial_fraction + parallel_fraction / num_processors)


def print_table():
    processors = [1, 2, 4, 8, 16, 32, 64, 128, 256, 1024]
    parallel_fractions = [0.50, 0.75, 0.90, 0.95, 0.99]

    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║                      AMDAHL'S LAW  - SPEEDUP TABLE                  ║")
    print("║           Speedup = 1 / ((1 - P) + P/N)                            ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()

    # Header
    header = f"{'P (parallel %)':<18}"
    for n in processors:
        header += f"{'N='+str(n):>8}"
    print(header)
    print("-" * len(header))

    # Rows
    for p in parallel_fractions:
        row = f"{p*100:>5.0f}%{'':>12}"
        for n in processors:
            speedup = amdahls_speedup(p, n)
            row += f"{speedup:>8.1f}"
        print(row)

    print()
    print("Key takeaways:")
    print("  - At P=50%, even 1024 servers give only 2.0x speedup")
    print("  - At P=95%, 32 servers give 12.5x (not 32x)")
    print("  - At P=99%, you approach N but never reach it")
    print("  - The serial portion (1-P) is the bottleneck ceiling")


def print_ascii_chart():
    print()
    print("SPEEDUP vs NUMBER OF SERVERS (ASCII Chart)")
    print()

    fractions = {"P=50%": 0.50, "P=75%": 0.75, "P=90%": 0.90, "P=95%": 0.95}
    max_n = 64
    chart_width = 50
    max_speedup = 20

    for label, p in fractions.items():
        points = []
        for n in range(1, max_n + 1):
            s = amdahls_speedup(p, n)
            points.append(s)

        # Normalize to chart width
        bar_len = int((points[-1] / max_speedup) * chart_width)
        bar = "█" * bar_len + "░" * (chart_width - bar_len)
        print(f"  {label:<8} |{bar}| {points[-1]:.1f}x (max ≈ {1/(1-p):.1f}x)")

    print(f"{'':>10}{'':>1}{'─' * chart_width}")
    print(f"{'':>10} 0x{'':<{chart_width-6}}{max_speedup}x")


def interactive_calculator():
    print()
    print("─" * 50)
    print("INTERACTIVE CALCULATOR")
    print("─" * 50)

    try:
        p = float(input("\nWhat % of your workload is parallelizable? (e.g. 90): "))
        p = p / 100.0
        n = int(input("How many servers/processors? (e.g. 16): "))

        speedup = amdahls_speedup(p, n)
        max_speedup = 1.0 / (1.0 - p)

        print(f"\nResults:")
        print(f"  Parallel fraction:  {p*100:.0f}%")
        print(f"  Serial fraction:    {(1-p)*100:.0f}%")
        print(f"  Processors:         {n}")
        print(f"  Speedup:            {speedup:.2f}x")
        print(f"  Max possible:       {max_speedup:.2f}x (with infinite processors)")
        print(f"  Efficiency:         {(speedup/n)*100:.1f}% (speedup / processors)")
    except (ValueError, ZeroDivisionError):
        print("Invalid input. Please enter numeric values.")


def main():
    print_table()
    print_ascii_chart()
    interactive_calculator()


if __name__ == "__main__":
    main()
