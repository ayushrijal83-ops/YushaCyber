"""Mission definitions — structured mission data.

Each mission is a dict with objectives. Missions are loaded by
the mission_loader and run by the mission_runner.
"""

from __future__ import annotations

from typing import Any

MISSIONS: dict[str, dict[str, Any]] = {
    "linux-basics": {
        "id": "linux-basics",
        "title": "Linux Basics",
        "description": "Learn essential Linux commands.",
        "difficulty": "Easy",
        "category": "linux",
        "xp_total": 200,
        "estimated_minutes": 15,
        "learn": ["Navigating the filesystem", "Listing & revealing hidden files",
                  "Reading files with cat", "Creating files & directories",
                  "Command history"],
        "objectives": [
            {
                "id": "lb-1",
                "title": "Where am I?",
                "description": "Use the command that shows your current working directory.",
                "hint": "The command is three letters: p, w, d.",
                "validate": {"type": "command", "match": "pwd"},
                "xp": 20,
            },
            {
                "id": "lb-2",
                "title": "List Files",
                "description": "List the contents of the current directory.",
                "hint": "Use 'ls' to list files.",
                "validate": {"type": "command", "match": "ls"},
                "xp": 20,
            },
            {
                "id": "lb-3",
                "title": "Hidden Files",
                "description": "List ALL files including hidden ones (files starting with a dot).",
                "hint": "Add the -la flag to ls.",
                "validate": {"type": "command", "match": "ls -la"},
                "xp": 25,
            },
            {
                "id": "lb-4",
                "title": "Change Directory",
                "description": "Navigate into the Documents folder.",
                "hint": "Use 'cd Documents'.",
                "validate": {"type": "cwd", "match": "/home/student/Documents"},
                "xp": 25,
            },
            {
                "id": "lb-5",
                "title": "Read a File",
                "description": "Read the contents of welcome.txt inside Documents.",
                "hint": "Use 'cat welcome.txt' (make sure you're in Documents).",
                "validate": {"type": "command", "match": "cat welcome.txt"},
                "xp": 25,
            },
            {
                "id": "lb-6",
                "title": "Create a File",
                "description": "Create a new file called notes.txt.",
                "hint": "Use 'touch notes.txt'.",
                "validate": {"type": "file_exists", "match": "/home/student/notes.txt"},
                "xp": 30,
            },
            {
                "id": "lb-7",
                "title": "Create a Folder",
                "description": "Create a new directory called practice.",
                "hint": "Use 'mkdir practice'.",
                "validate": {"type": "dir_exists", "match": "/home/student/practice"},
                "xp": 30,
            },
            {
                "id": "lb-8",
                "title": "View History",
                "description": "View your command history.",
                "hint": "Type 'history'.",
                "validate": {"type": "command", "match": "history"},
                "xp": 25,
            },
        ],
        "filesystem": {
            "home": {"student": {
                "Documents": {
                    "welcome.txt": "Welcome to YushaCyber!\nYou're learning Linux. Keep going!\n",
                    "readme.txt": "Read the welcome file first.\n",
                },
                "Downloads": {},
                "Desktop": {},
                ".bashrc": "# ~/.bashrc\n",
                ".profile": "# ~/.profile\n",
            }},
            "etc": {
                "passwd": "root:x:0:0:root:/root:/bin/bash\nstudent:x:1000:1000::/home/student:/bin/bash\n",
                "hostname": "yushacyber-lab\n",
            },
            "var": {"log": {"syslog": "System log entries here.\n"}},
            "tmp": {},
        },
        "next_mission": "linux-permissions",
    },
    "linux-permissions": {
        "id": "linux-permissions",
        "title": "Linux Permissions",
        "description": "Master file permissions, ownership, and chmod/chown on a realistic Linux-style filesystem.",
        "difficulty": "Beginner",
        "category": "linux",
        "xp_total": 200,
        "estimated_minutes": 20,
        "learn": ["Linux permissions", "Users", "Groups", "chmod",
                  "Ownership", "Permission notation"],
        "objectives": [
            {
                "id": "lp-1",
                "title": "Read Permission Notation",
                "description": "List the contents of ~/permissions in long format to see permission bits, owners, and groups.",
                "hint": "Use 'ls -l' (try it inside the permissions folder: cd permissions).",
                "validate": {"type": "command", "match": "ls -l"},
                "xp": 20,
            },
            {
                "id": "lp-2",
                "title": "Identify Yourself",
                "description": "Find out which user you're currently logged in as.",
                "hint": "The command is 'whoami'.",
                "validate": {"type": "command", "match": "whoami"},
                "xp": 15,
            },
            {
                "id": "lp-3",
                "title": "Inspect Your Identity",
                "description": "Inspect your full user and group ID information.",
                "hint": "Type 'id'.",
                "validate": {"type": "command", "match": "id"},
                "xp": 15,
            },
            {
                "id": "lp-4",
                "title": "Check Your Groups",
                "description": "List the groups you belong to.",
                "hint": "Type 'groups'.",
                "validate": {"type": "command", "match": "groups"},
                "xp": 15,
            },
            {
                "id": "lp-5",
                "title": "Access Denied",
                "description": "Try to read private.txt in ~/permissions and see what happens when you don't have permission.",
                "hint": "Use 'cat private.txt' — it should be denied.",
                "validate": {"type": "output_contains", "match": "permission denied"},
                "xp": 25,
            },
            {
                "id": "lp-6",
                "title": "Grant Read Access",
                "description": "Use chmod to make challenge.txt readable by everyone (mode 644).",
                "hint": "Use 'chmod 644 challenge.txt'.",
                "validate": {"type": "file_mode", "match": "644",
                             "path": "/home/student/permissions/challenge.txt"},
                "xp": 30,
            },
            {
                "id": "lp-7",
                "title": "Verify the Change",
                "description": "Confirm challenge.txt now shows the new permission bits by listing it directly.",
                "hint": "Use 'ls -l challenge.txt' (from ~/permissions) and check it changed to read for everyone.",
                "validate": {"type": "file_mode", "match": "644",
                             "path": "/home/student/permissions/challenge.txt"},
                "xp": 25,
            },
            {
                "id": "lp-8",
                "title": "Take Ownership",
                "description": "Take ownership of private.txt so you can finally read it.",
                "hint": "Use 'chown student private.txt'.",
                "validate": {"type": "file_owner", "match": "student",
                             "path": "/home/student/permissions/private.txt"},
                "xp": 55,
            },
        ],
        "filesystem": {
            "home": {"student": {
                "permissions": {
                    "public.txt": "Anyone can read this file. Permissions are your first line of defense.\n",
                    "private.txt": "Only the owner should be able to read this. If you can see this, ownership matters.\n",
                    "challenge.txt": "Locked down until you grant yourself read access.\n",
                },
                "Documents": {},
                "Downloads": {},
                "Desktop": {},
                ".bashrc": "# ~/.bashrc\n",
                ".profile": "# ~/.profile\n",
            }},
            "etc": {
                "passwd": "root:x:0:0:root:/root:/bin/bash\nstudent:x:1000:1000::/home/student:/bin/bash\n",
                "hostname": "yushacyber-lab\n",
            },
            "var": {"log": {"syslog": "System log entries here.\n"}},
            "tmp": {},
        },
        "permissions": {
            "/home/student/permissions/public.txt": {"mode": "644", "owner": "student", "group": "student"},
            "/home/student/permissions/private.txt": {"mode": "600", "owner": "root", "group": "root"},
            "/home/student/permissions/challenge.txt": {"mode": "000", "owner": "student", "group": "student"},
        },
        "next_mission": "bash-fundamentals",
    },
    "bash-fundamentals": {
        "id": "bash-fundamentals",
        "title": "Bash Fundamentals",
        "description": "Learn Bash scripting fundamentals — variables, environment variables, "
                       "command substitution, pipes, redirection, scripts, conditionals, and loops.",
        "difficulty": "Beginner",
        "category": "linux",
        "xp_total": 250,
        "estimated_minutes": 28,
        "learn": ["Variables", "echo", "Command substitution", "Environment variables",
                  "Pipes", "Redirection", "Simple shell scripts", "Executable permissions",
                  "Basic if statements", "Basic loops"],
        "objectives": [
            {
                "id": "bf-1",
                "title": "Navigate to Your Workspace",
                "description": "Move into your bash-lab workspace.",
                "hint": "Use 'cd bash-lab'.",
                "validate": {"type": "cwd", "match": "/home/student/bash-lab"},
                "xp": 10,
            },
            {
                "id": "bf-2",
                "title": "Create a Variable",
                "description": "Create a shell variable called name holding your identity.",
                "hint": 'Use name="student" — no spaces around the =.',
                "validate": {"type": "command", "match": "name="},
                "xp": 15,
            },
            {
                "id": "bf-3",
                "title": "Print the Variable",
                "description": "Print the value of the variable you just created.",
                "hint": 'Use echo "$name".',
                "validate": {"type": "output_contains", "match": "student"},
                "xp": 15,
            },
            {
                "id": "bf-4",
                "title": "Create an Environment Variable",
                "description": "Export an environment variable called LAB so child processes can see it.",
                "hint": 'Use export LAB="yushacyber".',
                "validate": {"type": "command", "match": "export lab"},
                "xp": 15,
            },
            {
                "id": "bf-5",
                "title": "Inspect the Environment Variable",
                "description": "Print the LAB environment variable.",
                "hint": 'Use echo "$LAB".',
                "validate": {"type": "output_contains", "match": "yushacyber"},
                "xp": 15,
            },
            {
                "id": "bf-6",
                "title": "Command Substitution",
                "description": "Store the output of another command inside a variable.",
                "hint": "Use current=$(pwd).",
                "validate": {"type": "command", "match": "$(pwd)"},
                "xp": 20,
            },
            {
                "id": "bf-7",
                "title": "Use a Pipe",
                "description": "Filter the workspace file listing so only .txt files show.",
                "hint": "Use ls | grep txt.",
                "validate": {"type": "output_contains", "match": "files.txt"},
                "xp": 20,
            },
            {
                "id": "bf-8",
                "title": "Redirect Output",
                "description": "Redirect the file listing into a new file called output.txt.",
                "hint": "Use ls > output.txt.",
                "validate": {"type": "file_exists", "match": "/home/student/bash-lab/output.txt"},
                "xp": 20,
            },
            {
                "id": "bf-9",
                "title": "Create a Bash Script",
                "description": "Write a one-line script.sh that prints a greeting.",
                "hint": 'Use echo \'echo "Hello from YushaCyber!"\' > script.sh.',
                "validate": {"type": "file_contains", "match": "Hello from YushaCyber",
                             "path": "/home/student/bash-lab/script.sh"},
                "xp": 20,
            },
            {
                "id": "bf-10",
                "title": "Make It Executable",
                "description": "Give script.sh executable permission.",
                "hint": "Use chmod +x script.sh.",
                "validate": {"type": "file_mode", "match": "755",
                             "path": "/home/student/bash-lab/script.sh"},
                "xp": 20,
            },
            {
                "id": "bf-11",
                "title": "Execute the Script",
                "description": "Run your script and see it print the greeting.",
                "hint": "Use ./script.sh.",
                "validate": {"type": "output_contains", "match": "Hello from YushaCyber"},
                "xp": 25,
            },
            {
                "id": "bf-12",
                "title": "Write a Conditional",
                "description": "Use an if statement to check that script.sh exists.",
                "hint": 'Use if [ -f script.sh ]; then echo "found"; fi.',
                "validate": {"type": "output_contains", "match": "found"},
                "xp": 30,
            },
            {
                "id": "bf-13",
                "title": "Write a Loop",
                "description": "Use a for loop to count from 1 to 3.",
                "hint": 'Use for i in 1 2 3; do echo "count-$i"; done.',
                "validate": {"type": "output_contains", "match": "count-3"},
                "xp": 25,
            },
        ],
        "filesystem": {
            "home": {"student": {
                "bash-lab": {
                    "files.txt": "sample data file\n",
                    "notes.md": "not a text export\n",
                },
                "Documents": {},
                "Downloads": {},
                "Desktop": {},
                ".bashrc": "# ~/.bashrc\n",
                ".profile": "# ~/.profile\n",
            }},
            "etc": {
                "passwd": "root:x:0:0:root:/root:/bin/bash\nstudent:x:1000:1000::/home/student:/bin/bash\n",
                "hostname": "yushacyber-lab\n",
            },
            "var": {"log": {"syslog": "System log entries here.\n"}},
            "tmp": {},
        },
        "next_mission": "networking-fundamentals",
    },
    "networking-fundamentals": {
        "id": "networking-fundamentals",
        "title": "Networking Fundamentals",
        "description": "Explore IP addressing, routing, DNS, and listening services on a "
                       "simulated Linux networking lab.",
        "difficulty": "Beginner",
        "category": "networking",
        "xp_total": 300,
        "estimated_minutes": 35,
        "learn": ["IP addresses", "IPv4", "Network interfaces", "Subnet masks",
                  "Default gateway", "DNS", "Ports", "TCP vs UDP",
                  "Basic connectivity", "Routing"],
        "objectives": [
            {
                "id": "net-1",
                "title": "Inspect Network Interfaces",
                "description": "List your machine's network interfaces and their addresses.",
                "hint": "Use 'ip addr'.",
                "validate": {"type": "command", "match": "ip addr"},
                "xp": 20,
            },
            {
                "id": "net-2",
                "title": "Identify Your IPv4 Address",
                "description": "Find your own IPv4 address in the interface list.",
                "hint": "Look for the 'inet' line under eth0.",
                "validate": {"type": "output_contains", "match": "10.10.10.20"},
                "xp": 20,
            },
            {
                "id": "net-3",
                "title": "Inspect the Routing Table",
                "description": "List the routes your machine knows about.",
                "hint": "Use 'ip route'.",
                "validate": {"type": "command", "match": "ip route"},
                "xp": 20,
            },
            {
                "id": "net-4",
                "title": "Identify the Default Gateway",
                "description": "Find the default gateway in the routing table.",
                "hint": "Look for the 'default via' line.",
                "validate": {"type": "output_contains", "match": "default via 10.10.10.1"},
                "xp": 20,
            },
            {
                "id": "net-5",
                "title": "Test Connectivity to the Gateway",
                "description": "Ping the default gateway to confirm you can reach it.",
                "hint": "Use 'ping 10.10.10.1'.",
                "validate": {"type": "output_contains", "match": "64 bytes from 10.10.10.1:"},
                "xp": 25,
            },
            {
                "id": "net-6",
                "title": "Test Connectivity to the Web Server",
                "description": "Ping the web server to confirm the lab network is reachable.",
                "hint": "Use 'ping 10.10.10.10'.",
                "validate": {"type": "output_contains", "match": "64 bytes from 10.10.10.10:"},
                "xp": 25,
            },
            {
                "id": "net-7",
                "title": "Inspect Listening Services",
                "description": "List the services listening on your own machine.",
                "hint": "Use 'ss'.",
                "validate": {"type": "command", "match": "ss"},
                "xp": 25,
            },
            {
                "id": "net-8",
                "title": "Identify an Open TCP Port",
                "description": "Find the open web server port (80) in the listening services.",
                "hint": "Look for the ':80' entry in the ss output.",
                "validate": {"type": "output_contains", "match": "10.10.10.20:80"},
                "xp": 30,
            },
            {
                "id": "net-9",
                "title": "Perform a DNS Lookup",
                "description": "Resolve example.local using the simulated DNS server.",
                "hint": "Use 'nslookup example.local'.",
                "validate": {"type": "output_contains", "match": "Address: 10.10.10.10"},
                "xp": 30,
            },
            {
                "id": "net-10",
                "title": "Inspect the Hosts File",
                "description": "Check the local hosts file for static name mappings.",
                "hint": "Use 'cat /etc/hosts'.",
                "validate": {"type": "output_contains", "match": "student-pc"},
                "xp": 25,
            },
            {
                "id": "net-11",
                "title": "Identify the DNS Server",
                "description": "Find the IP address of the simulated DNS server.",
                "hint": "Check the 'Server:' line from your nslookup output.",
                "validate": {"type": "output_contains", "match": "10.10.10.53"},
                "xp": 25,
            },
            {
                "id": "net-12",
                "title": "Final Networking Challenge",
                "description": "Confirm connectivity to the file server to complete the lab.",
                "hint": "Use 'ping 10.10.10.30'.",
                "validate": {"type": "output_contains", "match": "64 bytes from 10.10.10.30:"},
                "xp": 35,
            },
        ],
        "filesystem": {
            "home": {"student": {
                "Documents": {},
                "Downloads": {},
                "Desktop": {},
                ".bashrc": "# ~/.bashrc\n",
                ".profile": "# ~/.profile\n",
            }},
            "etc": {
                "passwd": "root:x:0:0:root:/root:/bin/bash\nstudent:x:1000:1000::/home/student:/bin/bash\n",
                "hostname": "yushacyber-lab\n",
                "hosts": "127.0.0.1 localhost\n"
                        "10.10.10.20 student-pc\n"
                        "10.10.10.1 gateway\n"
                        "10.10.10.10 example.local web01\n"
                        "10.10.10.53 dns01\n"
                        "10.10.10.30 fileserver.local fileserver\n",
            },
            "var": {"log": {"syslog": "System log entries here.\n"}},
            "tmp": {},
        },
        "network": {
            "student_ip": "10.10.10.20",
            "dns_server_ip": "10.10.10.53",
            "hosts": {
                "10.10.10.20": {
                    "hostname": "student-pc",
                    "interfaces": [
                        {"name": "eth0", "ip": "10.10.10.20", "cidr": 24, "state": "UP"},
                        {"name": "lo", "ip": "127.0.0.1", "cidr": 8, "state": "UP"},
                    ],
                    "routes": [
                        {"destination": "default", "via": "10.10.10.1",
                         "dev": "eth0", "is_default": True},
                        {"destination": "10.10.10.0/24", "dev": "eth0"},
                    ],
                    "services": [
                        {"port": 22, "proto": "tcp", "name": "ssh"},
                        {"port": 80, "proto": "tcp", "name": "http"},
                    ],
                },
                "10.10.10.1": {"hostname": "gateway", "reachable": True},
                "10.10.10.10": {"hostname": "web01", "reachable": True,
                                "services": [{"port": 80, "proto": "tcp", "name": "http"}]},
                "10.10.10.53": {"hostname": "dns01", "reachable": True,
                                "services": [{"port": 53, "proto": "udp", "name": "dns"}]},
                "10.10.10.30": {"hostname": "fileserver", "reachable": True,
                                "services": [{"port": 445, "proto": "tcp", "name": "smb"}]},
            },
            "dns_records": [
                {"hostname": "example.local", "ip": "10.10.10.10"},
                {"hostname": "fileserver.local", "ip": "10.10.10.30"},
            ],
        },
        "next_mission": "network-troubleshooting",
    },
    "network-troubleshooting": {
        "id": "network-troubleshooting",
        "title": "Network Troubleshooting",
        "description": "Diagnose and repair a broken simulated network by reasoning from "
                       "symptoms — interface, IP, gateway, DNS, and services — one layer "
                       "at a time.",
        "difficulty": "Beginner → Intermediate",
        "category": "networking",
        "xp_total": 350,
        "estimated_minutes": 40,
        "learn": ["Systematic troubleshooting", "Interface state", "IP/subnet mismatches",
                  "Default gateway misconfiguration", "DNS vs. connectivity failures",
                  "Service availability", "Simulated network repair"],
        "objectives": [
            {
                "id": "nt-1",
                "title": "Identify the Problem",
                "description": "Your network connection is broken. Try to reach the gateway and see what happens.",
                "hint": "Use 'ping 10.10.10.1'.",
                "validate": {"type": "output_contains", "match": "Network is unreachable"},
                "xp": 20,
            },
            {
                "id": "nt-2",
                "title": "Inspect the Interface",
                "description": "Check the state of your network interfaces.",
                "hint": "Use 'ip link'.",
                "validate": {"type": "command", "match": "ip link"},
                "xp": 15,
            },
            {
                "id": "nt-3",
                "title": "Identify the Interface Is Down",
                "description": "Confirm eth0 is reporting a DOWN state.",
                "hint": "Look at the 'state' field in the ip link output.",
                "validate": {"type": "output_contains", "match": "state DOWN"},
                "xp": 20,
            },
            {
                "id": "nt-4",
                "title": "Bring the Interface Up",
                "description": "Enable eth0 so the machine can use the network again.",
                "hint": "Use 'ip link set eth0 up'.",
                "validate": {"type": "network_state", "check": "interface_state",
                             "interface": "eth0", "match": "UP"},
                "xp": 30,
            },
            {
                "id": "nt-5",
                "title": "Inspect IP Configuration",
                "description": "Check the IP address currently assigned to eth0.",
                "hint": "Use 'ip addr'.",
                "validate": {"type": "command", "match": "ip addr"},
                "xp": 15,
            },
            {
                "id": "nt-6",
                "title": "Identify the IP Mismatch",
                "description": "The assigned address is on the wrong subnet for this network (10.10.10.0/24).",
                "hint": "Compare the address in 'ip addr' against the lab network range.",
                "validate": {"type": "output_contains", "match": "10.10.20.50"},
                "xp": 20,
            },
            {
                "id": "nt-7",
                "title": "Fix the IP Configuration",
                "description": "Assign the correct address for this network to eth0.",
                "hint": "Use 'ip addr add 10.10.10.20/24 dev eth0'.",
                "validate": {"type": "network_state", "check": "interface_ip",
                             "interface": "eth0", "match": "10.10.10.20"},
                "xp": 30,
            },
            {
                "id": "nt-8",
                "title": "Inspect Routing Configuration",
                "description": "Check the routing table for a default route.",
                "hint": "Use 'ip route'.",
                "validate": {"type": "command", "match": "ip route"},
                "xp": 15,
            },
            {
                "id": "nt-9",
                "title": "Identify the Wrong Gateway",
                "description": "The default route points to a gateway outside this network's range.",
                "hint": "Compare the 'via' address against 10.10.10.0/24.",
                "validate": {"type": "output_contains", "match": "10.10.20.1"},
                "xp": 20,
            },
            {
                "id": "nt-10",
                "title": "Fix the Default Gateway",
                "description": "Point the default route at the correct gateway.",
                "hint": "Use 'ip route add default via 10.10.10.1'.",
                "validate": {"type": "network_state", "check": "default_gateway",
                             "match": "10.10.10.1"},
                "xp": 30,
            },
            {
                "id": "nt-11",
                "title": "Verify Gateway Connectivity",
                "description": "Confirm you can now reach the gateway.",
                "hint": "Use 'ping 10.10.10.1'.",
                "validate": {"type": "output_contains", "match": "64 bytes from 10.10.10.1:"},
                "xp": 25,
            },
            {
                "id": "nt-12",
                "title": "Verify Remote Connectivity",
                "description": "Confirm you can now reach a host beyond the gateway.",
                "hint": "Use 'ping 10.10.10.10'.",
                "validate": {"type": "output_contains", "match": "64 bytes from 10.10.10.10:"},
                "xp": 30,
            },
            {
                "id": "nt-13",
                "title": "Diagnose the DNS Issue",
                "description": "Connectivity is restored, but name resolution still fails. "
                               "Confirm this is a DNS problem, not a network problem.",
                "hint": "Use 'nslookup example.local' — it fails even though ping works.",
                "validate": {"type": "output_contains", "match": "NXDOMAIN"},
                "xp": 35,
            },
            {
                "id": "nt-14",
                "title": "Complete the Network Audit",
                "description": "Finish up by confirming which services are running on your machine.",
                "hint": "Use 'ss'.",
                "validate": {"type": "command", "match": "ss"},
                "xp": 45,
            },
        ],
        "filesystem": {
            "home": {"student": {
                "Documents": {},
                "Downloads": {},
                "Desktop": {},
                ".bashrc": "# ~/.bashrc\n",
                ".profile": "# ~/.profile\n",
            }},
            "etc": {
                "passwd": "root:x:0:0:root:/root:/bin/bash\nstudent:x:1000:1000::/home/student:/bin/bash\n",
                "hostname": "yushacyber-lab\n",
                "hosts": "127.0.0.1 localhost\n"
                        "10.10.10.20 student-pc\n"
                        "10.10.10.1 gateway\n"
                        "10.10.10.10 example.local web01\n"
                        "10.10.10.53 dns01\n",
            },
            "var": {"log": {"syslog": "System log entries here.\n"}},
            "tmp": {},
        },
        "network": {
            "student_ip": "10.10.10.20",
            "dns_server_ip": "10.10.10.53",
            "dns_working": False,
            "hosts": {
                "10.10.10.20": {
                    "hostname": "student-pc",
                    "interfaces": [
                        {"name": "eth0", "ip": "10.10.20.50", "cidr": 24, "state": "DOWN"},
                        {"name": "lo", "ip": "127.0.0.1", "cidr": 8, "state": "UP"},
                    ],
                    "routes": [
                        {"destination": "default", "via": "10.10.20.1",
                         "dev": "eth0", "is_default": True},
                        {"destination": "10.10.10.0/24", "dev": "eth0"},
                    ],
                    "services": [
                        {"port": 22, "proto": "tcp", "name": "ssh"},
                        {"port": 80, "proto": "tcp", "name": "http"},
                    ],
                },
                "10.10.10.1": {"hostname": "gateway", "reachable": True},
                "10.10.10.10": {"hostname": "web01", "reachable": True,
                                "services": [{"port": 80, "proto": "tcp", "name": "http"}]},
                "10.10.10.53": {"hostname": "dns01", "reachable": True,
                                "services": [{"port": 53, "proto": "udp", "name": "dns"}]},
            },
            "dns_records": [
                {"hostname": "example.local", "ip": "10.10.10.10"},
            ],
        },
        "next_mission": "nmap-fundamentals",
    },
    "nmap-fundamentals": {
        "id": "nmap-fundamentals",
        "title": "Nmap Fundamentals",
        "description": "Learn network reconnaissance with Nmap on a fully simulated LAN. "
                       "Only ever scan systems you own or have explicit permission to "
                       "test — this mission is entirely simulated and never touches a "
                       "real host; never scan public IP addresses without authorization.",
        "difficulty": "Intermediate",
        "category": "networking",
        "xp_total": 400,
        "estimated_minutes": 45,
        "learn": ["Host discovery", "Port scanning", "TCP vs UDP ports",
                  "Open / closed / filtered states", "Service discovery",
                  "Version detection", "Basic OS detection", "Scan interpretation",
                  "Responsible reconnaissance"],
        "objectives": [
            {
                "id": "nm-1",
                "title": "Perform a Basic Scan",
                "description": "Run a default Nmap scan against the web server.",
                "hint": "Use 'nmap 10.10.10.10'.",
                "validate": {"type": "command", "match": "nmap 10.10.10.10"},
                "xp": 35,
            },
            {
                "id": "nm-2",
                "title": "Identify the Open SSH Port",
                "description": "Find the open SSH port in the scan results.",
                "hint": "Look for port 22 in the PORT/STATE/SERVICE table.",
                "validate": {"type": "output_contains", "match": "22/tcp open ssh"},
                "xp": 30,
            },
            {
                "id": "nm-3",
                "title": "Identify the HTTP Port",
                "description": "Find the open HTTP port in the scan results.",
                "hint": "Look for port 80 in the PORT/STATE/SERVICE table.",
                "validate": {"type": "output_contains", "match": "80/tcp open http"},
                "xp": 30,
            },
            {
                "id": "nm-4",
                "title": "Perform a Targeted Port Scan",
                "description": "Scan only the ports you care about instead of the full default set.",
                "hint": "Use 'nmap -p 22,80,443 10.10.10.10'.",
                "validate": {"type": "command", "match": "-p 22,80,443"},
                "xp": 40,
            },
            {
                "id": "nm-5",
                "title": "Perform Service/Version Detection",
                "description": "Find out what software is actually running behind each open port.",
                "hint": "Use 'nmap -sV 10.10.10.10'.",
                "validate": {"type": "command", "match": "-sv"},
                "xp": 40,
            },
            {
                "id": "nm-6",
                "title": "Identify the Web Server Service",
                "description": "Identify the web server software from your version scan.",
                "hint": "Check the VERSION column for the HTTP/HTTPS ports.",
                "validate": {"type": "output_contains", "match": "nginx"},
                "xp": 35,
            },
            {
                "id": "nm-7",
                "title": "Perform a TCP Connect Scan",
                "description": "Perform an explicit TCP connect scan against the web server.",
                "hint": "Use 'nmap -sT 10.10.10.10'.",
                "validate": {"type": "command", "match": "-st"},
                "xp": 35,
            },
            {
                "id": "nm-8",
                "title": "Perform a UDP Scan",
                "description": "Scan the DNS server's UDP service.",
                "hint": "Use 'nmap -sU 10.10.10.53'.",
                "validate": {"type": "output_contains", "match": "53/udp open dns"},
                "xp": 40,
            },
            {
                "id": "nm-9",
                "title": "Detect the OS on a Ping-Blocking Host",
                "description": "The training server blocks ICMP, so a normal scan reports it "
                               "down. Skip host discovery and attempt OS detection.",
                "hint": "Use 'nmap -Pn -O 10.10.10.40'.",
                "validate": {"type": "output_contains", "match": "Linux 5.X"},
                "xp": 45,
            },
            {
                "id": "nm-10",
                "title": "Final Reconnaissance Challenge",
                "description": "Run a full version scan against the file server and identify "
                               "every open, closed, and filtered port on it.",
                "hint": "Use 'nmap -sV 10.10.10.30'.",
                "validate": {"type": "output_contains", "match": "25/tcp filtered"},
                "xp": 70,
            },
        ],
        "filesystem": {
            "home": {"student": {
                "Documents": {},
                "Downloads": {},
                "Desktop": {},
                ".bashrc": "# ~/.bashrc\n",
                ".profile": "# ~/.profile\n",
            }},
            "etc": {
                "passwd": "root:x:0:0:root:/root:/bin/bash\nstudent:x:1000:1000::/home/student:/bin/bash\n",
                "hostname": "yushacyber-lab\n",
                "hosts": "127.0.0.1 localhost\n"
                        "10.10.10.20 student-pc\n"
                        "10.10.10.1 gateway\n"
                        "10.10.10.10 example.local web01\n"
                        "10.10.10.30 fileserver\n"
                        "10.10.10.40 training\n"
                        "10.10.10.53 dns01\n",
            },
            "var": {"log": {"syslog": "System log entries here.\n"}},
            "tmp": {},
        },
        "network": {
            "student_ip": "10.10.10.20",
            "dns_server_ip": "10.10.10.53",
            "hosts": {
                "10.10.10.20": {
                    "hostname": "student-pc",
                    "interfaces": [
                        {"name": "eth0", "ip": "10.10.10.20", "cidr": 24, "state": "UP"},
                        {"name": "lo", "ip": "127.0.0.1", "cidr": 8, "state": "UP"},
                    ],
                    "routes": [
                        {"destination": "default", "via": "10.10.10.1",
                         "dev": "eth0", "is_default": True},
                        {"destination": "10.10.10.0/24", "dev": "eth0"},
                    ],
                },
                "10.10.10.1": {"hostname": "gateway", "reachable": True},
                "10.10.10.10": {
                    "hostname": "web01", "reachable": True,
                    "services": [
                        {"port": 22, "proto": "tcp", "name": "ssh", "version": "OpenSSH 9.x"},
                        {"port": 80, "proto": "tcp", "name": "http", "version": "nginx"},
                        {"port": 443, "proto": "tcp", "name": "https", "version": "nginx"},
                    ],
                },
                "10.10.10.30": {
                    "hostname": "fileserver", "reachable": True,
                    "services": [
                        {"port": 21, "proto": "tcp", "name": "ftp", "version": "vsftpd 3.x"},
                        {"port": 22, "proto": "tcp", "name": "ssh", "version": "OpenSSH 9.x"},
                        {"port": 445, "proto": "tcp", "name": "microsoft-ds", "version": "Samba 4.x"},
                    ],
                    "filtered_ports": [25],
                },
                "10.10.10.53": {
                    "hostname": "dns01", "reachable": True,
                    "services": [{"port": 53, "proto": "udp", "name": "dns", "version": "BIND 9.x"}],
                },
                "10.10.10.40": {
                    "hostname": "training", "reachable": True, "blocks_icmp": True,
                    "os_guess": "Linux 5.X (embedded)",
                    "services": [
                        {"port": 22, "proto": "tcp", "name": "ssh", "version": "OpenSSH 8.x"},
                        {"port": 8080, "proto": "tcp", "name": "http-proxy", "version": "Squid 5.x"},
                    ],
                },
            },
            "dns_records": [
                {"hostname": "example.local", "ip": "10.10.10.10"},
            ],
        },
        "next_mission": "network-reconnaissance",
    },
    "network-reconnaissance": {
        "id": "network-reconnaissance",
        "title": "Network Reconnaissance",
        "description": "You are operating inside an authorized simulated training network. "
                       "Perform structured reconnaissance against the YushaCyber training "
                       "network to discover hosts, enumerate services, and identify the "
                       "primary target — building a documented, evidence-based conclusion "
                       "rather than a single lucky guess. Entirely simulated; nothing here "
                       "touches a real host or network.",
        "difficulty": "Intermediate",
        "category": "networking",
        "xp_total": 450,
        "estimated_minutes": 50,
        "learn": ["Host discovery", "Port enumeration", "Service identification",
                  "Version detection", "Attack-surface comparison", "Finding prioritization",
                  "Reconnaissance documentation", "Evidence-based conclusions"],
        "objectives": [
            {
                "id": "rn-1",
                "title": "Discover Hosts",
                "description": "Sweep the training network to see which hosts are alive.",
                "hint": "Use 'nmap -sn 10.10.10.0/24'.",
                "validate": {"type": "command", "match": "-sn 10.10.10.0/24"},
                "xp": 50,
            },
            {
                "id": "rn-2",
                "title": "Identify Interesting Hosts",
                "description": "Not every discovered host is equally interesting. Investigate "
                               "one of the real servers more closely (not the gateway).",
                "hint": "Try 'nmap 10.10.10.10', 'nmap 10.10.10.30', or 'nmap 10.10.10.40'.",
                "validate": {"type": "command", "match": ["nmap 10.10.10.10",
                                                          "nmap 10.10.10.30",
                                                          "nmap 10.10.10.40"]},
                "xp": 30,
            },
            {
                "id": "rn-3",
                "title": "Enumerate Target Ports",
                "description": "Do a full port sweep of the training server.",
                "hint": "Use 'nmap -p- 10.10.10.40'.",
                "validate": {"type": "command", "match": "-p- 10.10.10.40"},
                "xp": 35,
            },
            {
                "id": "rn-4",
                "title": "Identify Open Services",
                "description": "Confirm which services are running behind the open ports.",
                "hint": "Look for the MySQL entry in your port sweep.",
                "validate": {"type": "output_contains", "match": "3306/tcp open mysql"},
                "xp": 35,
            },
            {
                "id": "rn-5",
                "title": "Perform Service Detection",
                "description": "Identify the exact service versions running on the training server.",
                "hint": "Use 'nmap -sV 10.10.10.40'.",
                "validate": {"type": "output_contains", "match": "MySQL 8.x"},
                "xp": 40,
            },
            {
                "id": "rn-6",
                "title": "Compare Hosts",
                "description": "Compare the training server against another host to gauge "
                               "relative attack surface.",
                "hint": "Use 'nmap -sV 10.10.10.10' or 'nmap -sV 10.10.10.30'.",
                "validate": {"type": "command", "match": ["nmap -sv 10.10.10.10",
                                                          "nmap -sv 10.10.10.30"]},
                "xp": 35,
            },
            {
                "id": "rn-7",
                "title": "Identify High-Interest Ports",
                "description": "Some services deserve extra attention during recon: SSH, FTP, "
                               "MySQL, SMB, and exposed HTTP. Confirm the file server's SMB port.",
                "hint": "Use 'nmap -sV 10.10.10.30' and look for microsoft-ds.",
                "validate": {"type": "output_contains", "match": "445/tcp open microsoft-ds"},
                "xp": 35,
            },
            {
                "id": "rn-8",
                "title": "Build an Attack-Surface Inventory",
                "description": "Record the training server's findings in your recon notes.",
                "hint": 'Use echo "Host: 10.10.10.40 (training-server) - Ports: 22,3306,8080 - '
                       'Services: SSH,MySQL,HTTP" > recon/findings.txt.',
                "validate": {"type": "file_contains", "match": "3306",
                             "path": "/home/student/recon/findings.txt"},
                "xp": 40,
            },
            {
                "id": "rn-9",
                "title": "Identify the Primary Target",
                "description": "Based on your evidence, conclude which host is the primary "
                               "reconnaissance target and record it.",
                "hint": 'Use echo "TARGET: 10.10.10.40" >> recon/findings.txt.',
                "validate": {"type": "file_contains", "match": "TARGET: 10.10.10.40",
                             "path": "/home/student/recon/findings.txt"},
                "xp": 45,
            },
            {
                "id": "rn-10",
                "title": "Document Findings",
                "description": "Write a structured summary of the services you identified.",
                "hint": 'Use echo "Services: SSH,MySQL,HTTP" >> recon/findings.txt.',
                "validate": {"type": "file_contains", "match": "Services: SSH,MySQL,HTTP",
                             "path": "/home/student/recon/findings.txt"},
                "xp": 45,
            },
            {
                "id": "rn-11",
                "title": "Final Reconnaissance Challenge",
                "description": "Confirm your conclusion with a final justification based on "
                               "the full body of evidence you've gathered.",
                "hint": 'Use echo "PRIMARY TARGET CONFIRMED: 10.10.10.40 exposes SSH, MySQL, '
                       'and HTTP - highest service diversity" >> recon/findings.txt.',
                "validate": {"type": "file_contains", "match": "PRIMARY TARGET CONFIRMED",
                             "path": "/home/student/recon/findings.txt"},
                "xp": 60,
            },
        ],
        "filesystem": {
            "home": {"student": {
                "recon": {},
                "Documents": {},
                "Downloads": {},
                "Desktop": {},
                ".bashrc": "# ~/.bashrc\n",
                ".profile": "# ~/.profile\n",
            }},
            "etc": {
                "passwd": "root:x:0:0:root:/root:/bin/bash\nstudent:x:1000:1000::/home/student:/bin/bash\n",
                "hostname": "yushacyber-lab\n",
                "hosts": "127.0.0.1 localhost\n"
                        "10.10.10.20 student-pc\n"
                        "10.10.10.1 gateway\n"
                        "10.10.10.10 web-server\n"
                        "10.10.10.30 file-server\n"
                        "10.10.10.40 training-server\n"
                        "10.10.10.53 dns-server\n",
            },
            "var": {"log": {"syslog": "System log entries here.\n"}},
            "tmp": {},
        },
        "network": {
            "student_ip": "10.10.10.20",
            "dns_server_ip": "10.10.10.53",
            "hosts": {
                "10.10.10.20": {
                    "hostname": "student-machine",
                    "interfaces": [
                        {"name": "eth0", "ip": "10.10.10.20", "cidr": 24, "state": "UP"},
                        {"name": "lo", "ip": "127.0.0.1", "cidr": 8, "state": "UP"},
                    ],
                    "routes": [
                        {"destination": "default", "via": "10.10.10.1",
                         "dev": "eth0", "is_default": True},
                        {"destination": "10.10.10.0/24", "dev": "eth0"},
                    ],
                },
                "10.10.10.1": {"hostname": "gateway", "reachable": True},
                "10.10.10.10": {
                    "hostname": "web-server", "reachable": True,
                    "services": [
                        {"port": 22, "proto": "tcp", "name": "ssh", "version": "OpenSSH 9.x"},
                        {"port": 80, "proto": "tcp", "name": "http", "version": "nginx"},
                        {"port": 443, "proto": "tcp", "name": "https", "version": "nginx"},
                    ],
                },
                "10.10.10.30": {
                    "hostname": "file-server", "reachable": True,
                    "services": [
                        {"port": 21, "proto": "tcp", "name": "ftp", "version": "vsftpd 3.x"},
                        {"port": 22, "proto": "tcp", "name": "ssh", "version": "OpenSSH 9.x"},
                        {"port": 445, "proto": "tcp", "name": "microsoft-ds", "version": "Samba 4.x"},
                    ],
                },
                "10.10.10.40": {
                    "hostname": "training-server", "reachable": True,
                    "services": [
                        {"port": 22, "proto": "tcp", "name": "ssh", "version": "OpenSSH 8.x"},
                        {"port": 8080, "proto": "tcp", "name": "http", "version": "Apache 2.x"},
                        {"port": 3306, "proto": "tcp", "name": "mysql", "version": "MySQL 8.x"},
                    ],
                },
                "10.10.10.53": {
                    "hostname": "dns-server", "reachable": True,
                    "services": [{"port": 53, "proto": "udp", "name": "dns", "version": "BIND 9.x"}],
                },
            },
            "dns_records": [
                {"hostname": "example.local", "ip": "10.10.10.10"},
            ],
        },
        "next_mission": "wireshark-fundamentals",
    },
    "wireshark-fundamentals": {
        "id": "wireshark-fundamentals",
        "title": "Wireshark Fundamentals",
        "description": "Learn packet analysis on a fully simulated capture environment — "
                       "read Ethernet/IPv4/TCP/UDP layers, recognize the TCP three-way "
                       "handshake, analyze DNS and HTTP traffic, follow conversations, "
                       "apply display filters, and investigate a capture for unusual "
                       "traffic. Entirely simulated; no real packet is ever captured, "
                       "inspected, or transmitted.",
        "difficulty": "Intermediate",
        "category": "networking",
        "xp_total": 450,
        "estimated_minutes": 50,
        "learn": ["Packet structure", "Ethernet frames", "IPv4 headers", "TCP vs UDP",
                  "Source/destination ports", "TCP flags", "TCP three-way handshake",
                  "DNS analysis", "HTTP analysis", "Following conversations",
                  "Display filters", "Investigating suspicious traffic"],
        "objectives": [
            {
                "id": "wf-1",
                "title": "Open the Packet Capture",
                "description": "Load the TCP handshake capture to begin your analysis.",
                "hint": "Use 'capture handshake'.",
                "validate": {"type": "command", "match": "capture handshake"},
                "xp": 35,
            },
            {
                "id": "wf-2",
                "title": "Identify Source and Destination IPs",
                "description": "Inspect the first packet's IP layer.",
                "hint": "Use 'show 1'.",
                "validate": {"type": "output_contains", "match": "Source: 10.10.10.20"},
                "xp": 30,
            },
            {
                "id": "wf-3",
                "title": "Identify TCP Traffic",
                "description": "Filter the capture to show only TCP packets.",
                "hint": "Use 'filter tcp'.",
                "validate": {"type": "command", "match": "filter tcp"},
                "xp": 25,
            },
            {
                "id": "wf-4",
                "title": "Identify the Three-Way Handshake",
                "description": "Recognize the SYN, SYN-ACK, ACK sequence that opens a "
                               "TCP connection.",
                "hint": "Use 'follow 1' to see the full sequence.",
                "validate": {"type": "output_contains", "match": "SYN, ACK"},
                "xp": 45,
            },
            {
                "id": "wf-5",
                "title": "Identify Source and Destination Ports",
                "description": "Find the port numbers involved in the handshake.",
                "hint": "Use 'show 1' and check the TCP layer.",
                "validate": {"type": "output_contains", "match": "Destination Port: 80"},
                "xp": 30,
            },
            {
                "id": "wf-6",
                "title": "Filter DNS Traffic",
                "description": "Switch to the mixed capture and isolate the DNS lookup.",
                "hint": "Use 'capture mixed' then 'filter dns'.",
                "validate": {"type": "output_contains", "match": "example.training"},
                "xp": 35,
            },
            {
                "id": "wf-7",
                "title": "Analyze an HTTP Request",
                "description": "Load the HTTP capture and identify the request method and path.",
                "hint": "Use 'capture http' then 'filter http'.",
                "validate": {"type": "output_contains", "match": "GET /index.html"},
                "xp": 45,
            },
            {
                "id": "wf-8",
                "title": "Follow a TCP Conversation",
                "description": "Follow the full sequence of packets belonging to one exchange.",
                "hint": "Use 'follow 1' (or any packet number in the current capture).",
                "validate": {"type": "output_contains", "match": "Conversation:"},
                "xp": 30,
            },
            {
                "id": "wf-9",
                "title": "Use an IP Filter",
                "description": "Filter packets by a specific IP address.",
                "hint": "Use 'filter ip.addr == 10.10.10.10'.",
                "validate": {"type": "command", "match": "ip.addr == 10.10.10.10"},
                "xp": 30,
            },
            {
                "id": "wf-10",
                "title": "Use a Port Filter",
                "description": "Filter packets by TCP port 80.",
                "hint": "Use 'filter tcp.port == 80'.",
                "validate": {"type": "command", "match": "tcp.port == 80"},
                "xp": 30,
            },
            {
                "id": "wf-11",
                "title": "Analyze Mixed Traffic",
                "description": "Review the mixed capture and recognize the different "
                               "protocols in play, including background UDP traffic.",
                "hint": "Use 'capture mixed' then 'packets'.",
                "validate": {"type": "output_contains", "match": "UDP"},
                "xp": 45,
            },
            {
                "id": "wf-12",
                "title": "Final Investigation",
                "description": "A training workstation is behaving strangely. Load the "
                               "investigation capture, find the unusual connection, and "
                               "record which host and port it involves.",
                "hint": 'Use "capture investigation", find the odd connection, then '
                       'echo "Source: 10.10.10.20, Destination: 10.10.10.77, Port: 4444, '
                       'Protocol: TCP, Reason: uncommon destination and port not part '
                       'of normal training traffic" > wireshark/investigation.txt.',
                "validate": {"type": "file_contains", "match": "10.10.10.77",
                             "path": "/home/student/wireshark/investigation.txt"},
                "xp": 70,
            },
        ],
        "filesystem": {
            "home": {"student": {
                "wireshark": {},
                "Documents": {},
                "Downloads": {},
                "Desktop": {},
                ".bashrc": "# ~/.bashrc\n",
                ".profile": "# ~/.profile\n",
            }},
            "etc": {
                "passwd": "root:x:0:0:root:/root:/bin/bash\nstudent:x:1000:1000::/home/student:/bin/bash\n",
                "hostname": "yushacyber-lab\n",
            },
            "var": {"log": {"syslog": "System log entries here.\n"}},
            "tmp": {},
        },
        "packet_captures": ["handshake", "dns", "http", "icmp", "mixed", "investigation"],
        "next_mission": "web-fundamentals",
    },
    "web-fundamentals": {
        "id": "web-fundamentals",
        "title": "Web Fundamentals",
        "description": "Learn how modern web applications communicate — URL structure, "
                       "HTTP methods and status codes, headers, query parameters, forms, "
                       "cookies, and sessions — against a fully simulated training site "
                       "(CyberShop). This is the first mission in the Web Security path; "
                       "it is purely educational, not an exploitation exercise, and never "
                       "makes a real network request to any host.",
        "difficulty": "Intermediate",
        "category": "web",
        "xp_total": 450,
        "estimated_minutes": 50,
        "learn": ["URL structure", "HTTP requests", "HTTP responses", "HTTP methods",
                  "Status codes", "Headers", "Query parameters", "Request bodies",
                  "Cookies", "Sessions", "Forms", "Redirects"],
        "objectives": [
            {
                "id": "wb-1",
                "title": "Understand URL Structure",
                "description": "Open a product page and identify the scheme, host, path, "
                               "and query parameter in its URL.",
                "hint": "Use 'open https://cybershop.training/products?id=42'.",
                "validate": {"type": "web_state", "check": "query_param",
                             "param": "id", "match": "42"},
                "xp": 45,
            },
            {
                "id": "wb-2",
                "title": "Make a GET Request",
                "description": "Request the products page and confirm the HTTP method used.",
                "hint": "Use 'request GET /products'.",
                "validate": {"type": "web_state", "check": "method", "match": "GET"},
                "xp": 25,
            },
            {
                "id": "wb-3",
                "title": "Inspect a Query Parameter",
                "description": "Search the site and identify the query parameter name and value.",
                "hint": "Use 'open https://cybershop.training/search?q=linux'.",
                "validate": {"type": "web_state", "check": "query_param",
                             "param": "q", "match": "linux"},
                "xp": 30,
            },
            {
                "id": "wb-4",
                "title": "Understand a 200 OK Response",
                "description": "Open a valid page and confirm it returns 200 OK.",
                "hint": "Use 'open https://cybershop.training/'.",
                "validate": {"type": "web_state", "check": "status_code", "match": "200"},
                "xp": 25,
            },
            {
                "id": "wb-5",
                "title": "Find a 404 Response",
                "description": "Request a page that doesn't exist and confirm the status code.",
                "hint": "Use 'open https://cybershop.training/does-not-exist'.",
                "validate": {"type": "web_state", "check": "status_code", "match": "404"},
                "xp": 30,
            },
            {
                "id": "wb-6",
                "title": "Inspect Request Headers",
                "description": "Check the Host header your own request sent.",
                "hint": "Use 'headers' after making a request.",
                "validate": {"type": "web_state", "check": "header", "in": "request",
                             "header": "Host", "match": "cybershop.training"},
                "xp": 30,
            },
            {
                "id": "wb-7",
                "title": "Inspect Response Headers",
                "description": "Check the Content-Type header the server responded with.",
                "hint": "Use 'headers' after making a request.",
                "validate": {"type": "web_state", "check": "header", "in": "response",
                             "header": "Content-Type", "match": "text/html"},
                "xp": 30,
            },
            {
                "id": "wb-8",
                "title": "Submit the Login Form",
                "description": "Submit the login form and confirm the request's content type.",
                "hint": 'Use \'open -X POST -d "username=student&password=training123" '
                       "https://cybershop.training/login'.",
                "validate": {"type": "web_state", "check": "header", "in": "request",
                             "header": "Content-Type", "match": "application/x-www-form-urlencoded"},
                "xp": 35,
            },
            {
                "id": "wb-9",
                "title": "Inspect Set-Cookie",
                "description": "After a successful login, identify the session cookie you received.",
                "hint": "Use 'cookies' after logging in.",
                "validate": {"type": "web_state", "check": "cookie",
                             "cookie_name": "session_id", "match": "student-session"},
                "xp": 35,
            },
            {
                "id": "wb-10",
                "title": "Use the Session Cookie",
                "description": "Request your profile and confirm the server recognizes your session.",
                "hint": "Use 'open https://cybershop.training/profile'.",
                "validate": {"type": "web_state", "check": "session_authenticated", "match": "true"},
                "xp": 35,
            },
            {
                "id": "wb-11",
                "title": "Analyze a Redirect",
                "description": "Request the login page and identify where it redirects to.",
                "hint": "Use 'open https://cybershop.training/login'.",
                "validate": {"type": "web_state", "check": "redirect_location",
                             "match": "/auth/login"},
                "xp": 50,
            },
            {
                "id": "wb-12",
                "title": "Final Web Investigation",
                "description": "A user reports they cannot access their profile. Inspect the "
                               "investigation log and determine why, using evidence from the "
                               "HTTP exchange, then record your conclusion.",
                "hint": 'Use \'evidence\' to list the log, \'inspect 1\'/\'inspect 2\'/'
                       "'inspect 3' to read each exchange, then "
                       'echo "Conclusion: the user never submitted the login form, so no '
                       'session cookie was ever set - no session cookie" > web/investigation.txt.',
                "validate": {"type": "file_contains", "match": "no session cookie",
                             "path": "/home/student/web/investigation.txt"},
                "xp": 80,
            },
        ],
        "filesystem": {
            "home": {"student": {
                "web": {},
                "Documents": {},
                "Downloads": {},
                "Desktop": {},
                ".bashrc": "# ~/.bashrc\n",
                ".profile": "# ~/.profile\n",
            }},
            "etc": {
                "passwd": "root:x:0:0:root:/root:/bin/bash\nstudent:x:1000:1000::/home/student:/bin/bash\n",
                "hostname": "yushacyber-lab\n",
            },
            "var": {"log": {"syslog": "System log entries here.\n"}},
            "tmp": {},
        },
        "web_lab": True,
        "next_mission": None,
    },
}


def get_mission(mission_id: str) -> dict[str, Any] | None:
    return MISSIONS.get(mission_id)


def list_missions() -> list[dict[str, Any]]:
    return [{"id": m["id"], "title": m["title"],
             "difficulty": m["difficulty"], "xp_total": m["xp_total"],
             "objectives": len(m["objectives"])}
            for m in MISSIONS.values()]
