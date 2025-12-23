mkdir -p results

for c in 10 25 50 100 200 400 800 1000; do
  wrk -t10 -c"$c" -d30s --latency "http://localhost:$BUN_PORT/no" | tee "results/bun_c${c}.txt"
done

for c in 10 25 50 100 200 400 800 1000; do
  wrk -t10 -c"$c" -d30s --latency "http://localhost:$NODE_PORT/no" | tee "results/node_c${c}.txt"
done