import argparse
import time

from .scenarios import load_scenario
from .config import load_config
from .agents import LoadAgent, ControlAgent, RedisLoadAgent

def main():
    parser = argparse.ArgumentParser(description="Distributed test orchestrator.")
    parser.add_argument(
        "--scenario",
        type=str,
        required=True,
        help="Path to scenario YAML file (e.g. scenarios/node_failure.yaml)",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        required=True,
        help="Identifier for this run (used for logs/metrics directory)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["http", "redis"],
        default="http",
        help="Which system to drive: 'http' (FastAPI nodes) or 'redis' (redis-node-1/2).",
    )
    args = parser.parse_args()
    config = load_config()

    scenario = load_scenario(args.scenario)

    print(f"Loaded scenario: {scenario.name}")
    print(f"Description: {scenario.description}\n")

    control_agent = ControlAgent()

    # Select nodes + load agent based on mode
    if args.mode == "http":
        nodes = config.get(
            "http_nodes",
            [
                "http://localhost:8001",
                "http://localhost:8002",
                "http://localhost:8003",
            ],
        )
        load_agent = LoadAgent(nodes=nodes, run_id=args.run_id, rps=0.0)
        killable_services = config.get(
            "http_services",
            ["service-node-1", "service-node-2", "service-node-3"],
        )

    else:  # redis mode
        nodes = config.get(
            "redis_nodes",
            [
                "redis://localhost:6379",
                "redis://localhost:6380",
            ],
        )
        load_agent = RedisLoadAgent(hosts=nodes, run_id=args.run_id, rps=0.0)
        killable_services = config.get(
            "redis_services",
            ["redis-node-1", "redis-node-2"],
        )

    try:
        for i, phase in enumerate(scenario.phases, start=1):
            print(f"=== Phase {i}: {phase.name} (duration: {phase.duration_sec}s) ===")

            for action in phase.actions:
                print(f"  -> Executing action: {action.type} (target={action.target}, params={action.params})")

                if action.type == "start_load":
                    rps = action.params.get("rps", 10)
                    load_agent.start_load(rps=rps)

                elif action.type == "continue_load":
                    rps = action.params.get("rps", 10)
                    load_agent.update_rps(rps=rps)

                elif action.type == "kill_node":
                    # We assume target matches a service name in docker-compose
                    if action.target not in killable_services:
                        print(f"  [WARN] kill_node target {action.target} not recognized for mode {args.mode}")
                    control_agent.stop_container(action.target)

                elif action.type == "restart_node":
                    if action.target not in killable_services:
                        print(f"  [WARN] restart_node target {action.target} not recognized for mode {args.mode}")
                    control_agent.start_container(action.target)

                else:
                    print(f"  [WARN] Unknown action type: {action.type}")

            time.sleep(phase.duration_sec)

    finally:
        print("Stopping load agent...")
        load_agent.stop()
        print("Run complete.")


if __name__ == "__main__":
    main()