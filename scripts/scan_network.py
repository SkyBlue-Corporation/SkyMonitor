import json
import random

#example fictif : replace ping /nmap real

hosts = ["192.168.1.2", "192.168.1.3", "192.168.1.4"]
metrics = {}

for host in hosts:
    metrics[hosts] = {
                    "ram": random.randint(1, 100),
                    "cpu": random.randint(1, 100),
                    "uptime": f"{random.randint(1, 100)}h"
    }
    with open('merics.json', 'w')as f:
        json.dump(metrics, f, indent=4)