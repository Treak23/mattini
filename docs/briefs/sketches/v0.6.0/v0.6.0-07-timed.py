import resource, subprocess, sys, time
t = time.monotonic()
done = subprocess.run(sys.argv[1:])
wall = time.monotonic() - t
peak = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024
print(f"timed: exit {done.returncode} wall {wall:.1f} s peak {peak:.0f} MiB", file=sys.stderr)
sys.exit(done.returncode)
