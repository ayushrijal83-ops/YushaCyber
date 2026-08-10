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
        "next_mission": "http-deep-dive",
    },
    "http-deep-dive": {
        "id": "http-deep-dive",
        "title": "HTTP Deep Dive",
        "description": "Go beyond the basics: JSON APIs, the Authorization header, Referer, "
                       "cache headers, URL-encoding, and reconstructing a multi-request chain "
                       "from history — against the same simulated training site (CyberShop), "
                       "extended with a JSON API surface. Still purely educational: no "
                       "injection, no session hijacking, no real network request ever made.",
        "difficulty": "Intermediate",
        "category": "Web Security",
        "xp_total": 500,
        "estimated_minutes": 55,
        "learn": ["JSON request/response bodies", "Authorization header", "Referer header",
                  "Cache-Control / ETag", "URL encoding", "Request history",
                  "Redirect-chain reconstruction", "Cookie vs token auth"],
        "objectives": [
            {
                "id": "hd-1",
                "title": "Identify the Request Line",
                "description": "Request the products page and identify the method, path, and "
                               "protocol on the request line.",
                "hints": [
                    "Every HTTP request starts with one line: METHOD PATH PROTOCOL.",
                    ("Make any request against the simulated site, then look at the first "
                     "line of what 'inspect' or the Request tab shows you."),
                    "Use 'open https://cybershop.training/products'.",
                ],
                "validate": {"type": "web_state", "check": "path", "match": "/products"},
                "xp": 30,
            },
            {
                "id": "hd-2",
                "title": "Identify the Status Line",
                "description": "Make a request and identify the status line of the response.",
                "hints": [
                    "A response's first line is PROTOCOL STATUS_CODE REASON.",
                    ("Make a request, then check 'response' or the Response tab for the "
                     "status line."),
                    "Use 'open https://cybershop.training/' then 'response'.",
                ],
                "validate": {"type": "web_state", "check": "status_code", "match": "200"},
                "xp": 25,
            },
            {
                "id": "hd-3",
                "title": "Inspect a Request Header",
                "description": "Check the User-Agent header your own request sent.",
                "hints": [
                    ("Every request you send carries a User-Agent header identifying your "
                     "client, even though you never typed it."),
                    "Make a request, then use 'headers' to see the Request headers section.",
                    "Use 'headers' after making any request — look for User-Agent.",
                ],
                "validate": {"type": "web_state", "check": "header", "in": "request",
                             "header": "User-Agent", "match": "YushaCyber-Trainer/1.0"},
                "xp": 30,
            },
            {
                "id": "hd-4",
                "title": "Inspect a Response Header",
                "description": "Check the Server header the simulated site responds with.",
                "hints": [
                    "Responses carry their own headers, separate from the request's.",
                    "Make a request, then use 'headers' to see the Response headers section.",
                    "Use 'headers' after making any request — look for Server.",
                ],
                "validate": {"type": "web_state", "check": "header", "in": "response",
                             "header": "Server", "match": "CyberShop-Sim/1.0"},
                "xp": 30,
            },
            {
                "id": "hd-5",
                "title": "Understand Form Encoding",
                "description": "Submit the login form and confirm the 'username' field the "
                               "server actually received.",
                "hints": [
                    "HTML forms send data as key=value pairs joined with '&' in the body.",
                    "POST to /auth/login with a body like username=...&password=....",
                    ('Use \'open -X POST -d "username=student&password=training123" '
                     "https://cybershop.training/auth/login'."),
                ],
                "validate": {"type": "web_state", "check": "body_field", "in": "request",
                             "field": "username", "match": "student"},
                "xp": 35,
            },
            {
                "id": "hd-6",
                "title": "Understand a JSON Request",
                "description": "Send a JSON body to the profile API and confirm the request's "
                               "content type.",
                "hints": [
                    ("A JSON request needs its Content-Type header set explicitly — the "
                     "simulator won't guess it for you like it does for form data."),
                    ("Use '-H' to set 'Content-Type: application/json' alongside '-d' with a "
                     "JSON string, targeting /api/profile."),
                    ('Use \'open -X POST -H "Content-Type: application/json" -d '
                     "'{\"bio\": \"training\"}' https://cybershop.training/api/profile'."),
                ],
                "validate": {"type": "web_state", "check": "header", "in": "request",
                             "header": "Content-Type", "match": "application/json"},
                "xp": 35,
            },
            {
                "id": "hd-7",
                "title": "Decode a URL-Encoded Query",
                "description": "Search using a URL-encoded space in the query string and "
                               "confirm the decoded value.",
                "hints": [
                    "URLs can't contain literal spaces — they're encoded as %20.",
                    "Search for something with a space in it, percent-encoded in the URL.",
                    "Use 'open https://cybershop.training/search?q=web%20security'.",
                ],
                "validate": {"type": "web_state", "check": "query_param",
                             "param": "q", "match": "web security"},
                "xp": 30,
            },
            {
                "id": "hd-8",
                "title": "Analyze a Redirect",
                "description": "Request the login page and identify where it redirects to.",
                "hints": [
                    ("A 3xx response tells the client to go somewhere else — check its "
                     "Location header."),
                    ("Request the login page and look at the response's status code and "
                     "headers."),
                    "Use 'open https://cybershop.training/login'.",
                ],
                "validate": {"type": "web_state", "check": "redirect_location",
                             "match": "/auth/login"},
                "xp": 35,
            },
            {
                "id": "hd-9",
                "title": "Analyze the Session Cookie",
                "description": "Log in and identify the session cookie you received.",
                "hints": [
                    ("A successful login response sets a cookie the server will recognize "
                     "on later requests."),
                    "Submit the login form, then check what's in your cookie jar.",
                    ('After logging in with \'open -X POST -d '
                     '"username=student&password=training123" '
                     "https://cybershop.training/auth/login', use 'cookies'."),
                ],
                "validate": {"type": "web_state", "check": "cookie",
                             "cookie_name": "session_id", "match": "student-session"},
                "xp": 35,
            },
            {
                "id": "hd-10",
                "title": "Analyze the Authorization Header",
                "description": "Access the token-protected API endpoint using a Bearer token "
                               "instead of a session cookie.",
                "hints": [
                    ("Not every protected endpoint uses cookies — some expect a token in "
                     "the Authorization header instead."),
                    ("The training token is a fixed value: training-token-001, sent as "
                     "'Bearer <token>'."),
                    ('Use \'open -H "Authorization: Bearer training-token-001" '
                     "https://cybershop.training/api/me'."),
                ],
                "validate": {"type": "web_state", "check": "body_field", "in": "response",
                             "field": "username", "match": "student"},
                "xp": 35,
            },
            {
                "id": "hd-11",
                "title": "Analyze the Referer Header",
                "description": "Make a request that carries a Referer header and confirm its "
                               "value.",
                "hints": [
                    ("Referer tells the server which page the request 'came from' — note "
                     "the HTTP spec's spelling."),
                    ("Set it explicitly with '-H', since a fresh request has none by "
                     "default."),
                    ('Use \'open -H "Referer: https://cybershop.training/" '
                     "https://cybershop.training/products'."),
                ],
                "validate": {"type": "web_state", "check": "header", "in": "request",
                             "header": "Referer", "match": "https://cybershop.training/"},
                "xp": 30,
            },
            {
                "id": "hd-12",
                "title": "Analyze Cache Headers",
                "description": "Request a specific product and confirm its Cache-Control "
                               "header.",
                "hints": [
                    ("Cache-Control and ETag tell a client how long it may reuse a response "
                     "without asking again."),
                    "Only a specific product page (with an id) carries cache headers here.",
                    "Use 'open https://cybershop.training/products?id=42'.",
                ],
                "validate": {"type": "web_state", "check": "header", "in": "response",
                             "header": "Cache-Control", "match": "max-age=60"},
                "xp": 30,
            },
            {
                "id": "hd-13",
                "title": "Reconstruct a Request Chain",
                "description": "Reproduce the full login chain, in order: visit the login "
                               "page, follow the redirect, then submit the form.",
                "hints": [
                    ("A real browser doesn't make one request — it follows a chain: the "
                     "login link, the page the redirect points to, then the form submit."),
                    ("You must make all three requests, in this order, in one session — "
                     "'requests' shows your history so far."),
                    ("Run, in order: 'open https://cybershop.training/login', then "
                     "'open https://cybershop.training/auth/login', then "
                     '\'open -X POST -d "username=student&password=training123" '
                     "https://cybershop.training/auth/login'."),
                ],
                "validate": {"type": "web_state", "check": "history_sequence",
                             "match": ["GET /login", "GET /auth/login", "POST /auth/login"]},
                "xp": 60,
            },
            {
                "id": "hd-14",
                "title": "FINAL INVESTIGATION",
                "description": "A user reports their profile 'loads incorrectly' after "
                               "logging in successfully. Inspect the investigation log and "
                               "determine the actual root cause from the evidence, then "
                               "record your conclusion.",
                "hints": [
                    ("The login and redirect and cookie all worked correctly — look closer "
                     "at the very last response."),
                    ("Compare the final response's Content-Type against what a normal HTML "
                     "profile page should return."),
                    ("Use 'evidence' to list the log, then 'inspect 1' through 'inspect 4' "
                     "to read each exchange — the last entry's Content-Type is the bug. "
                     'Then: echo "Conclusion: the profile response Content-Type is '
                     'application/json instead of text/html" > web/http-investigation.txt.'),
                ],
                "validate": {"type": "file_contains", "match": "application/json",
                             "path": "/home/student/web/http-investigation.txt"},
                "xp": 60,
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
        "web_lab": "content-type-bug",
        "next_mission": "burp-fundamentals",
    },
    "burp-fundamentals": {
        "id": "burp-fundamentals",
        "title": "Burp Suite Fundamentals",
        "description": "Learn how an intercepting proxy works through a safe, fully simulated "
                       "Burp-style workflow: intercept, forward, drop, modify requests, review "
                       "history, use Repeater, compare responses, and understand proxy scope — "
                       "against the same simulated training site (CyberShop). Still purely "
                       "educational: no injection, no session hijacking, no real proxy or real "
                       "network request ever made.",
        "difficulty": "Intermediate",
        "category": "Web Security",
        "xp_total": 550,
        "estimated_minutes": 60,
        "learn": ["HTTP proxy architecture", "Intercept / forward / drop", "Request modification",
                  "Header and body editing", "HTTP history", "Repeater", "Response comparison",
                  "Proxy scope"],
        "objectives": [
            {
                "id": "bf-1",
                "title": "Understand Proxy Architecture",
                "description": "Check the proxy status and identify the Browser -> Proxy -> "
                               "Server flow and the current scope.",
                "hints": [
                    "A proxy sits between your browser and the server, able to see every request.",
                    "There's a dedicated command that shows the proxy's current status.",
                    "Use 'proxy'.",
                ],
                "validate": {"type": "command", "match": "proxy"},
                "xp": 30,
            },
            {
                "id": "bf-2",
                "title": "Enable Interception",
                "description": "Turn interception on so future requests are held before "
                               "reaching the server.",
                "hints": [
                    "Interception is off by default — requests pass straight through.",
                    "There's an 'intercept' command that takes on/off.",
                    "Use 'intercept on'.",
                ],
                "validate": {"type": "web_state", "check": "proxy_enabled", "match": "true"},
                "xp": 30,
            },
            {
                "id": "bf-3",
                "title": "Intercept a GET Request",
                "description": "With intercept on, request the products page and capture it "
                               "before it reaches the simulated server.",
                "hints": [
                    "Once intercept is on, any request you make gets held, not sent.",
                    "Make a normal 'open' request like you did in earlier missions.",
                    "Use 'open https://cybershop.training/products'.",
                ],
                "validate": {"type": "web_state", "check": "request_intercepted", "match": "1"},
                "xp": 35,
            },
            {
                "id": "bf-4",
                "title": "Forward the Request",
                "description": "Release the intercepted request to the simulated server and "
                               "verify the response.",
                "hints": [
                    "An intercepted request needs an explicit action to continue on.",
                    "There's a command that sends the held request through.",
                    "Use 'forward'.",
                ],
                "validate": {"type": "web_state", "check": "request_forwarded", "match": "1"},
                "xp": 35,
            },
            {
                "id": "bf-5",
                "title": "Drop a Request",
                "description": "Intercept another request, then discard it instead of "
                               "forwarding it.",
                "hints": [
                    "Not every intercepted request needs to reach the server.",
                    "Intercept one (e.g. a search), then use the opposite of 'forward'.",
                    "Use 'open https://cybershop.training/search?q=linux' then 'drop'.",
                ],
                "validate": {"type": "web_state", "check": "request_dropped", "match": "1"},
                "xp": 35,
            },
            {
                "id": "bf-6",
                "title": "Modify a Query Parameter",
                "description": "Intercept a request for product 42, change it to product 43, "
                               "then forward it.",
                "hints": [
                    "Once a request is intercepted, you can change it before it goes out.",
                    "There's an 'edit' command; 'edit query KEY VALUE' changes a query parameter.",
                    ("Use 'open https://cybershop.training/products?id=42', then "
                     "'edit query id 43', then 'forward'."),
                ],
                "validate": {"type": "web_state", "check": "query_param", "param": "id", "match": "43"},
                "xp": 40,
            },
            {
                "id": "bf-7",
                "title": "Modify a Request Header",
                "description": "Intercept a request, change its User-Agent header, then "
                               "forward it.",
                "hints": [
                    "Headers can be edited the same way query parameters can.",
                    "Use 'edit header NAME VALUE' on an intercepted request.",
                    ("Use 'open https://cybershop.training/products', then "
                     "'edit header User-Agent CyberBrowser/2.0', then 'forward'."),
                ],
                "validate": {"type": "web_state", "check": "header", "in": "request",
                             "header": "User-Agent", "match": "CyberBrowser/2.0"},
                "xp": 40,
            },
            {
                "id": "bf-8",
                "title": "Modify a POST Body",
                "description": "Log in first, then intercept a profile update, change the "
                               "display_name field, forward it, and confirm the simulated "
                               "server accepted the change.",
                "hints": [
                    ("You need a session cookie before /api/profile will accept anything — log "
                     "in first (intercept can be off for that step)."),
                    ("Then intercept a POST to /api/profile with a JSON body, and use "
                     "'edit body ...' to change the display_name field before forwarding."),
                    ('Use \'open -X POST -d "username=student&password=training123" '
                     "https://cybershop.training/auth/login' with intercept off, then "
                     "'intercept on', then 'open -X POST -H \"Content-Type: application/json\" "
                     '-d \'{"display_name": "Student"}\' https://cybershop.training/api/profile\', '
                     "then 'edit body '{\"display_name\": \"CyberStudent\"}'', then 'forward'."),
                ],
                "validate": {"type": "web_state", "check": "body_field", "in": "request",
                             "field": "display_name", "match": "CyberStudent"},
                "xp": 45,
            },
            {
                "id": "bf-9",
                "title": "Inspect HTTP History",
                "description": "Review your request history — you should have made several "
                               "requests by now.",
                "hints": [
                    "Every request the proxy has forwarded (dropped ones don't count) is logged.",
                    "There's a command that lists your history, same as earlier missions.",
                    "Use 'requests' to see the full list.",
                ],
                "validate": {"type": "web_state", "check": "request_count", "match": "5"},
                "xp": 30,
            },
            {
                "id": "bf-10",
                "title": "Send a Request to Repeater",
                "description": "Load a request from your history into Repeater.",
                "hints": [
                    "Repeater lets you resend and tweak one specific request repeatedly.",
                    "There's a 'repeater' command that takes a history entry number.",
                    "Use 'repeater 2' (or just 'repeater' for your most recent request).",
                ],
                "validate": {"type": "web_state", "check": "repeater_used", "match": "1"},
                "xp": 35,
            },
            {
                "id": "bf-11",
                "title": "Modify the Repeater Request",
                "description": "Change a query parameter on the request loaded in Repeater, "
                               "then send it.",
                "hints": [
                    "'edit' also works on whatever request is currently loaded in Repeater.",
                    "Change the parameter, then use Repeater's own send command.",
                    "Use 'edit query id 77', then 'repeater send'.",
                ],
                "validate": {"type": "web_state", "check": "query_param", "param": "id", "match": "77"},
                "xp": 40,
            },
            {
                "id": "bf-12",
                "title": "Compare Two Responses",
                "description": "Compare two responses from your history and identify what's "
                               "different between them.",
                "hints": [
                    "The proxy can line up two past responses side by side.",
                    "There's a 'compare' command that takes two history entry numbers.",
                    "Use 'compare 2 6' (or any two entries with different product IDs).",
                ],
                "validate": {"type": "web_state", "check": "response_compared", "match": "1"},
                "xp": 45,
            },
            {
                "id": "bf-13",
                "title": "Understand Proxy Scope",
                "description": "Attempt to request a host outside the training scope and "
                               "confirm the proxy blocks it.",
                "hints": [
                    "The proxy only ever operates against cybershop.training — nothing else.",
                    "Try 'open'-ing a URL for a completely different host.",
                    "Use 'open https://evil.example.com/'.",
                ],
                "validate": {"type": "web_state", "check": "scope_blocked", "match": "1"},
                "xp": 35,
            },
            {
                "id": "bf-14",
                "title": "FINAL CHALLENGE — Proxy Investigation",
                "description": "A user reports their profile information is not displaying "
                               "correctly after they update it. Intercept their profile-update "
                               "request, inspect it, identify the parameter problem, correct "
                               "it, forward it, confirm the fix, re-send it via Repeater, "
                               "compare the broken and fixed responses, then record your "
                               "conclusion.",
                "hints": [
                    ("Something about the request's body doesn't match what the server expects "
                     "— check the exact field name being sent versus what actually updates the "
                     "profile."),
                    ("Intercept a POST to /api/profile with 'Display_Name' (capital letters) in "
                     "the JSON body — the server accepts it (200 OK) but silently ignores it. "
                     "Fix the key, forward, then compare against the broken one."),
                    ("Use 'open -X POST -H \"Content-Type: application/json\" -d "
                     '\'{"Display_Name": "Alex Rivera"}\' https://cybershop.training/api/profile\' '
                     "then 'forward' (broken — note the history number). Then repeat with "
                     '\'{"display_name": "Alex Rivera"}\' (correct key) and \'forward\' (fixed — '
                     "note that history number). Use 'repeater N' then 'repeater send' on the "
                     "fixed one, then 'compare BROKEN FIXED'. Finally: "
                     'echo "Conclusion: the POST body used the wrong field name Display_Name '
                     "instead of display_name, so the update was silently ignored\" > "
                     "web/proxy-investigation.txt."),
                ],
                "validate": {"type": "file_contains", "match": "display_name",
                             "path": "/home/student/web/proxy-investigation.txt"},
                "xp": 75,
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
        "web_lab": "profile-mismatch",
        "next_mission": "authentication-sessions",
    },
    "authentication-sessions": {
        "id": "authentication-sessions",
        "title": "Authentication & Sessions",
        "description": "Learn how web authentication actually works — login, sessions, "
                       "cookies, protected routes, logout, and session expiration — against "
                       "the same simulated training site (CyberShop), using the same proxy "
                       "and Repeater from YC-035.2. Still purely educational: no session "
                       "hijacking, no credential attacks, no real authentication provider, "
                       "and no real network request ever made. Session exploitation is out "
                       "of scope for this mission — it belongs to a later one.",
        "difficulty": "Intermediate",
        "category": "Web Security",
        "xp_total": 600,
        "estimated_minutes": 65,
        "learn": ["Authentication vs. authorization", "Login flow", "Logout flow",
                  "HTTP POST login requests", "Set-Cookie vs. Cookie", "Session identifiers",
                  "Authenticated vs. unauthenticated requests", "Protected routes",
                  "Session invalidation", "Session expiration", "401 vs. 403 vs. 302"],
        "objectives": [
            {
                "id": "as-1",
                "title": "Authentication vs. Authorization",
                "description": "Authentication asks 'who are you?'; authorization asks 'what "
                               "are you allowed to do?'. Check the simulated site's status "
                               "before you log in.",
                "hints": [
                    ("There's a command that shows the simulated site, your login status, "
                     "and its routes — the same one from earlier missions."),
                    "It's a single short word.",
                    "Use 'web'.",
                ],
                "validate": {"type": "command", "match": "web"},
                "xp": 30,
            },
            {
                "id": "as-2",
                "title": "The Login Request",
                "description": "Submit the training login form and identify the HTTP method "
                               "the browser actually sends.",
                "hints": [
                    ("A login form submit is never a GET — it carries a body with your "
                     "credentials."),
                    "POST to /login (or /auth/login) with username and password in the body.",
                    ('Use \'open -X POST -d "username=student&password=training123" '
                     "https://cybershop.training/login'."),
                ],
                "validate": {"type": "web_state", "check": "method", "match": "POST"},
                "xp": 30,
            },
            {
                "id": "as-3",
                "title": "Fictional Training Credentials",
                "description": "Confirm the exact password your request sent. This is a "
                               "fixed, fictional training value — never a real password, "
                               "here or anywhere else.",
                "hints": [
                    ("Credentials are sent as form fields in the POST body — username and "
                     "password."),
                    "Check the 'password' field of the request you just sent.",
                    ("It should read training123 — the fixed training-only password for "
                     "the account 'student'."),
                ],
                "validate": {"type": "web_state", "check": "body_field", "in": "request",
                             "field": "password", "match": "training123"},
                "xp": 30,
            },
            {
                "id": "as-4",
                "title": "Successful Login",
                "description": "Confirm that a successful login doesn't return an HTML page "
                               "directly — it redirects the browser somewhere else.",
                "hints": [
                    "A successful login response here is a redirect, not a rendered page.",
                    "Check the status code of your last login response.",
                    "It should be 302 Found.",
                ],
                "validate": {"type": "web_state", "check": "status_code", "match": "302"},
                "xp": 35,
            },
            {
                "id": "as-5",
                "title": "Set-Cookie: Server to Browser",
                "description": "Find the session cookie the server set on your successful "
                               "login. Set-Cookie flows from server to browser.",
                "hints": [
                    ("A successful login tells the browser to remember a session — check "
                     "what landed in your cookie jar."),
                    "Use 'cookies' to see what's currently stored.",
                    "You should see session_id=student-session.",
                ],
                "validate": {"type": "web_state", "check": "cookie",
                             "cookie_name": "session_id", "match": "student-session"},
                "xp": 35,
            },
            {
                "id": "as-6",
                "title": "Cookie: Browser to Server",
                "description": "Request your profile and confirm your browser actually "
                               "attached the session cookie to the outgoing request. Cookie "
                               "flows from browser to server — the opposite direction of "
                               "Set-Cookie.",
                "hints": [
                    ("Set-Cookie and Cookie are opposite directions of the same value, not "
                     "two different things."),
                    ("Make a request to a page that needs your session now that you have "
                     "the cookie."),
                    ("Use 'open https://cybershop.training/profile', then check the request "
                     "carried Cookie: session_id=student-session."),
                ],
                "validate": {"type": "web_state", "check": "cookie_sent",
                             "cookie_name": "session_id", "match": "student-session"},
                "xp": 35,
            },
            {
                "id": "as-7",
                "title": "An Authenticated Request",
                "description": "Confirm the server recognized your session and actually "
                               "returned your profile.",
                "hints": [
                    ("If the cookie matches a real, current session, the server treats you "
                     "as logged in."),
                    "Check the status code and body of your last /profile request.",
                    "It should be 200 OK, with 'student' in the response body.",
                ],
                "validate": {"type": "web_state", "check": "session_authenticated", "match": "true"},
                "xp": 40,
            },
            {
                "id": "as-8",
                "title": "Failed Login",
                "description": "Submit incorrect training credentials and identify the "
                               "resulting status code.",
                "hints": [
                    ("Try the right username with a wrong password — this won't disturb "
                     "your existing session."),
                    "POST to /login with a bad password field.",
                    ('Use \'open -X POST -d "username=student&password=wrong-password" '
                     "https://cybershop.training/login' — expect 401 Unauthorized."),
                ],
                "validate": {"type": "web_state", "check": "status_code", "match": "401"},
                "xp": 35,
            },
            {
                "id": "as-9",
                "title": "Authenticated but Not Authorized",
                "description": "While still logged in as 'student', request /admin. You are "
                               "authenticated — but that doesn't mean you're allowed here.",
                "hints": [
                    ("Authentication succeeding doesn't automatically grant access to "
                     "everything."),
                    ("Request the admin route with your current (student) session cookie "
                     "still active."),
                    ("Use 'open https://cybershop.training/admin' — expect 403 Forbidden, "
                     "not 401."),
                ],
                "validate": {"type": "web_state", "check": "status_code", "match": "403"},
                "xp": 45,
            },
            {
                "id": "as-10",
                "title": "API Authentication",
                "description": "Inspect the session-protected profile API and identify the "
                               "authenticated username in the JSON response.",
                "hints": [
                    ("Not every protected endpoint returns HTML — this one returns JSON, "
                     "still gated by the same session cookie."),
                    "Request /api/profile with your session cookie attached.",
                    ("Use 'open https://cybershop.training/api/profile' — check the "
                     "'username' field in the response body."),
                ],
                "validate": {"type": "web_state", "check": "body_field", "in": "response",
                             "field": "username", "match": "student"},
                "xp": 40,
            },
            {
                "id": "as-11",
                "title": "Logout",
                "description": "Log out and inspect the response for a session cookie "
                               "deletion.",
                "hints": [
                    ("Logging out needs to tell both the server (invalidate the session) "
                     "and the browser (delete the cookie)."),
                    ("POST to /logout with your session cookie attached, then check the "
                     "response headers for a Set-Cookie deletion."),
                    ("Use 'open -X POST https://cybershop.training/logout' with your cookie "
                     "still set — look for 'Set-Cookie: session_id=; Max-Age=0'."),
                ],
                "validate": {"type": "web_state", "check": "logout_completed",
                             "cookie_name": "session_id", "match": "1"},
                "xp": 40,
            },
            {
                "id": "as-12",
                "title": "Session Invalidation",
                "description": "After logging out, request /profile again and confirm your "
                               "old session no longer works.",
                "hints": [
                    ("Logout doesn't just clear the browser's cookie — it invalidates the "
                     "session on the server too."),
                    "Request the same protected page you accessed earlier.",
                    ("Use 'open https://cybershop.training/profile' — expect 401 "
                     "Unauthorized, since you're no longer logged in."),
                ],
                "validate": {"type": "web_state", "check": "status_code", "match": "401"},
                "xp": 40,
            },
            {
                "id": "as-13",
                "title": "A Protected Route Redirects",
                "description": "Not every protected page answers with a bare error code — "
                               "some redirect you straight back to the login page. Request "
                               "/dashboard now that you're logged out.",
                "hints": [
                    ("A browser-style page often redirects an unauthenticated visitor "
                     "instead of showing a raw error status."),
                    "Request /dashboard while you have no valid session.",
                    ("Use 'open https://cybershop.training/dashboard' — its Location header "
                     "should point to /login."),
                ],
                "validate": {"type": "web_state", "check": "redirect_location", "match": "/login"},
                "xp": 40,
            },
            {
                "id": "as-14",
                "title": "Session Expiration",
                "description": "Log back in, then trigger simulated session expiration and "
                               "confirm the session no longer authenticates you — even though "
                               "your browser never deleted the cookie.",
                "hints": [
                    ("Expiration is different from logout: the browser keeps the cookie, "
                     "but the server stops recognizing it."),
                    ("Log in again first (your old session is gone), then use the dedicated "
                     "expiration command."),
                    ('Use \'open -X POST -d "username=student&password=training123" '
                     "https://cybershop.training/login', then 'expire'."),
                ],
                "validate": {"type": "web_state", "check": "session_expired", "match": "1"},
                "xp": 45,
            },
            {
                "id": "as-15",
                "title": "FINAL INVESTIGATION — The Missing Session",
                "description": "A student says they logged in successfully, but after "
                               "logging out they can no longer access their profile. "
                               "Inspect the investigation log, reconstruct the full "
                               "lifecycle from the evidence, and determine whether this is "
                               "actually a bug.",
                "hints": [
                    ("Every request in this log succeeds exactly as it should — look "
                     "closely at what happens between the third and fourth entries."),
                    ("The logout response includes a cookie deletion. The final /profile "
                     "request is correctly rejected because the session no longer exists "
                     "server-side — that's the system working as intended, not a bug."),
                    ('Use \'evidence\' to list the log, then \'inspect 1\' through '
                     "'inspect 4' to read each exchange. Then: "
                     'echo "Conclusion: logout invalidated the session server-side '
                     '(Set-Cookie deletion), so the final /profile request was correctly '
                     'rejected - not a bug" > web/auth-investigation.txt.'),
                ],
                "validate": {"type": "file_contains", "match": "invalidated the session",
                             "path": "/home/student/web/auth-investigation.txt"},
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
        "web_lab": "auth-lifecycle",
        "next_mission": "sql-injection-fundamentals",
    },
    "sql-injection-fundamentals": {
        "id": "sql-injection-fundamentals",
        "title": "SQL Injection Fundamentals",
        "description": "Learn how unsafe, string-concatenated database queries let user "
                       "input change a query's own logic — against the same simulated "
                       "training site (CyberShop) and the same Proxy/Repeater from "
                       "YC-035.2. The simulator recognizes only a fixed set of exact "
                       "training payloads and maps each to a predetermined, deterministic "
                       "outcome — it never parses or executes anything you type as real "
                       "SQL, never touches a real database, and never lets you escape the "
                       "training environment. No real exploitation tooling, no arbitrary "
                       "SQL execution, no data dumping — that's out of scope everywhere.",
        "difficulty": "Intermediate",
        "category": "Web Security",
        "xp_total": 700,
        "estimated_minutes": 70,
        "learn": ["What a database query is", "How web input reaches a database query",
                  "Unsafe string concatenation", "SQL injection", "Error-based clues",
                  "Boolean-based behavior differences", "The UNION concept (conceptual)",
                  "Authentication-bypass concept", "Parameterized queries / prepared statements",
                  "Why parameterized queries prevent injection", "Input boundaries",
                  "Evidence-based vulnerability confirmation"],
        "objectives": [
            {
                "id": "si-1",
                "title": "Database Basics",
                "description": "A database stores the site's data (products, users, "
                               "orders, reviews) so the application can look it up on "
                               "demand. Inspect the training database's schema before "
                               "touching any query.",
                "hints": [
                    "There's a read-only command that lists every table in the training database.",
                    "It's a single short word.",
                    "Use 'schema' to see the users, products, orders, and reviews tables.",
                ],
                "validate": {"type": "command", "match": "schema"},
                "xp": 30,
            },
            {
                "id": "si-2",
                "title": "Query Flow",
                "description": "Every search follows the same path: your input -> the "
                               "application -> a database query -> the database -> the "
                               "response you see. Check the simulated site's overview to "
                               "see the routes involved.",
                "hints": [
                    ("The same overview command from earlier missions lists this "
                     "mission's routes too."),
                    "It's a single short word.",
                    "Use 'web'.",
                ],
                "validate": {"type": "command", "match": "web"},
                "xp": 30,
            },
            {
                "id": "si-3",
                "title": "Normal Search",
                "description": "Search the training catalog for 'laptop' and observe a "
                               "normal, unmodified result.",
                "hints": [
                    ("A plain keyword, with no quotes or special characters, is always "
                     "treated as literal search text."),
                    "Request /search with q set to 'laptop'.",
                    "Use 'open https://cybershop.training/search?q=laptop'.",
                ],
                "validate": {"type": "web_state", "check": "normal_request", "param": "q", "match": "laptop"},
                "xp": 35,
            },
            {
                "id": "si-4",
                "title": "Inspect Request",
                "description": "Capture your search request using the Proxy before it "
                               "reaches the server.",
                "hints": [
                    ("Turn interception on first, the same way you did in the Burp "
                     "Suite mission."),
                    "Use 'intercept on', then make a search request.",
                    "Use 'intercept on', then 'open https://cybershop.training/search?q=keyboard'.",
                ],
                "validate": {"type": "web_state", "check": "request_intercepted", "match": "1"},
                "xp": 35,
            },
            {
                "id": "si-5",
                "title": "Identify Input",
                "description": "Identify 'q' as the user-controlled parameter by "
                               "requesting /search with q set to 'laptop' again.",
                "hints": [
                    ("Look at the request you captured — exactly one part of it changes "
                     "when you change your search term."),
                    "It's the query string parameter in the URL.",
                    ("Forward or make a request where q=laptop, then check the 'q' "
                     "query parameter."),
                ],
                "validate": {"type": "web_state", "check": "query_param", "param": "q", "match": "laptop"},
                "xp": 35,
            },
            {
                "id": "si-6",
                "title": "Error Clue",
                "description": "Send a single unescaped quote as the search term and "
                               "observe the simulated database error. This is a strong "
                               "clue that your input is landing directly inside the query.",
                "hints": [
                    "A lone quote character, with nothing else, is the training payload here.",
                    "Set q to a single ' character.",
                    ('Use: open "https://cybershop.training/search?q=\'" '
                     "— expect 500 Internal Server Error."),
                ],
                "validate": {"type": "web_state", "check": "error_observed", "match": "1"},
                "xp": 45,
            },
            {
                "id": "si-7",
                "title": "Boolean TRUE",
                "description": "Send the training condition that always evaluates true "
                               "and observe every product in the catalog come back.",
                "hints": [
                    ("The training payload closes the string early, then OR's in a "
                     "condition that's always true."),
                    "Set q to \"' OR '1'='1\" exactly.",
                    "Use 'open \"https://cybershop.training/search?q=' OR '1'='1\"'.",
                ],
                "validate": {"type": "web_state", "check": "boolean_true_observed", "match": "1"},
                "xp": 45,
            },
            {
                "id": "si-8",
                "title": "Boolean FALSE",
                "description": "Send the training condition that always evaluates false "
                               "and observe zero results, even though the catalog isn't empty.",
                "hints": [
                    ("Same idea as the TRUE condition, but the appended condition is "
                     "always false instead."),
                    "Set q to \"' AND '1'='2\" exactly.",
                    "Use 'open \"https://cybershop.training/search?q=' AND '1'='2\"'.",
                ],
                "validate": {"type": "web_state", "check": "boolean_false_observed", "match": "1"},
                "xp": 45,
            },
            {
                "id": "si-9",
                "title": "Compare Responses",
                "description": "Compare your TRUE and FALSE results using the Proxy's "
                               "Compare feature. The application's behavior clearly "
                               "depends on the condition you supplied — the core signal "
                               "of a boolean-based SQL injection.",
                "hints": [
                    "You already have both requests in your History — find their entry numbers.",
                    "Use 'compare N M' with the TRUE and FALSE request numbers.",
                    "Example: 'compare 1 2' (use your actual history numbers).",
                ],
                "validate": {"type": "web_state", "check": "response_difference", "match": "1"},
                "xp": 45,
            },
            {
                "id": "si-10",
                "title": "Query Structure",
                "description": "Inspect the simulated query representation for one of "
                               "your training requests and identify how unsafe string "
                               "concatenation let your input change the query's structure.",
                "hints": [
                    ("There's a command that shows Input -> Application Query -> "
                     "Database -> Response for your last request."),
                    "It's a single short word.",
                    "Use 'query' right after sending one of the TRUE/FALSE/error requests.",
                ],
                "validate": {"type": "web_state", "check": "query_structure_inspected", "match": "1"},
                "xp": 45,
            },
            {
                "id": "si-11",
                "title": "Authentication Scenario",
                "description": "Open the simulated vulnerable training login and submit "
                               "the normal training credentials.",
                "hints": [
                    ("This is a different endpoint from the /login you used in the "
                     "Authentication & Sessions mission."),
                    "POST to /training-login with username and password in the body.",
                    ('Use \'open -X POST -d "username=student&password=training123" '
                     "https://cybershop.training/training-login'."),
                ],
                "validate": {"type": "web_state", "check": "training_auth_scenario", "match": "opened"},
                "xp": 30,
            },
            {
                "id": "si-12",
                "title": "Authentication Logic",
                "description": "Complete the controlled authentication-bypass exercise "
                               "using only the predefined training username. A comment "
                               "sequence in the username can remove the rest of an unsafe "
                               "query — including the password check.",
                "hints": [
                    ("The training username ends the string early, then comments out "
                     "everything after it — including the password check."),
                    "Set username to admin'-- exactly; the password can be anything.",
                    ('Use: open -X POST -d "username=admin\'--&password=x" '
                     "https://cybershop.training/training-login "
                     "— expect authenticated_as: admin."),
                ],
                "validate": {"type": "web_state", "check": "training_auth_scenario", "match": "bypassed"},
                "xp": 55,
            },
            {
                "id": "si-13",
                "title": "Secure Endpoint",
                "description": "Send the exact same TRUE training input to /secure-search "
                               "and observe that the query structure stays unchanged.",
                "hints": [
                    "This endpoint treats your input as data, never as part of the query.",
                    "Request /secure-search with the same q you used for the TRUE condition.",
                    ("Use 'open \"https://cybershop.training/secure-search?q=' OR '1'='1\"' "
                     "— expect 0 matches, not every product."),
                ],
                "validate": {"type": "web_state", "check": "secure_endpoint_tested", "endpoint": "/secure-search", "match": "1"},
                "xp": 45,
            },
            {
                "id": "si-14",
                "title": "Parameterized Queries",
                "description": "Having tested both endpoints with the same input, "
                               "confirm why parameterized queries prevent injection: they "
                               "keep user input as data, never as part of the query's syntax.",
                "hints": [
                    ("Compare the two 'Application Query' lines you saw from 'query' on "
                     "each endpoint."),
                    ("One shows your input inside the query text; the other shows a "
                     "fixed placeholder that never changes."),
                    ("Make sure you've tested the same training input against both "
                     "/search and /secure-search, then use 'query' on each."),
                ],
                "validate": {"type": "web_state", "check": "parameterized_query_identified", "match": "1"},
                "xp": 45,
            },
            {
                "id": "si-15",
                "title": "Evidence Collection",
                "description": "Before the final investigation, make sure you've "
                               "gathered every kind of evidence: the TRUE/FALSE behavior "
                               "difference, at least one query representation, and the "
                               "secure endpoint's result.",
                "hints": [
                    ("Nothing new to send here — just make sure you've completed the "
                     "TRUE, FALSE, query-inspection, and secure-endpoint objectives above."),
                    "If any of those are still incomplete, go back and finish them first.",
                    ("Once TRUE, FALSE, a query inspection, and the secure endpoint are "
                     "all done, this objective completes automatically."),
                ],
                "validate": {"type": "web_state", "check": "evidence_collected", "match": "1"},
                "xp": 55,
            },
            {
                "id": "si-16",
                "title": "FINAL INVESTIGATION — The Inconsistent Search",
                "description": "A bug report says the training site's search "
                               "'sometimes returns every product, and sometimes returns "
                               "none, for no obvious reason.' Inspect the investigation "
                               "log, reconstruct what's actually happening from the "
                               "evidence, and determine whether this is SQL injection.",
                "hints": [
                    ("Look closely at the second and third entries — the query text, "
                     "not just the result count."),
                    ("The second and third requests are the TRUE/FALSE training "
                     "conditions — unsafe string concatenation let them change the "
                     "query's own logic. The fourth entry sends the same input to the "
                     "secure endpoint and gets a normal, unaffected result — proof "
                     "that parameterized queries are the fix."),
                    ("Use 'evidence' to list the log, then 'inspect 1' through "
                     "'inspect 4' to read each exchange. Then: "
                     'echo "Conclusion: unsafe string concatenation let the TRUE and '
                     "FALSE training conditions change the search query's own logic "
                     "- this is SQL injection. The secure endpoint returned a normal, "
                     "unaffected result for the same input because parameterized "
                     'queries keep input as data, never as query syntax." > '
                     "web/sqli-investigation.txt."),
                ],
                "validate": {"type": "file_contains", "match": "parameterized queries",
                             "path": "/home/student/web/sqli-investigation.txt"},
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
        "web_lab": "sqli-investigation",
        "next_mission": "xss-fundamentals",
    },
    "xss-fundamentals": {
        "id": "xss-fundamentals",
        "title": "Cross-Site Scripting Fundamentals",
        "description": "Learn how unsafe HTML rendering lets untrusted input become "
                       "part of the page itself — reflected, stored, and DOM-based XSS "
                       "— against the same simulated training site (CyberShop) and the "
                       "same Proxy/Repeater from YC-035.2. The simulator recognizes only "
                       "a fixed set of exact training markers and maps each to a "
                       "predetermined, deterministic 'simulated browser event' — it "
                       "never executes anything you type as real JavaScript, never "
                       "touches a real browser, cookie, or localStorage, and never lets "
                       "you escape the training environment. No real exploitation "
                       "tooling, no cookie/credential theft, no payload generators — "
                       "that's out of scope everywhere.",
        "difficulty": "Intermediate",
        "category": "Web Security",
        "xp_total": 750,
        "estimated_minutes": 70,
        "learn": ["What XSS is and why it happens", "Reflected XSS", "Stored XSS",
                  "DOM-based XSS (conceptual)", "Source and sink", "HTML context",
                  "Output encoding / HTML escaping", "Trusted vs. untrusted data",
                  "Content Security Policy (conceptual)", "Vulnerable vs. secure rendering",
                  "Evidence-based vulnerability confirmation"],
        "objectives": [
            {
                "id": "xs-1",
                "title": "XSS Basics",
                "description": "Cross-Site Scripting happens when untrusted input is "
                               "rendered as part of a page's HTML instead of as inert "
                               "text. Check the simulated site's overview to see this "
                               "mission's new routes.",
                "hints": [
                    ("The same overview command from earlier missions lists this "
                     "mission's routes too."),
                    "It's a single short word.",
                    "Use 'web'.",
                ],
                "validate": {"type": "command", "match": "web"},
                "xp": 35,
            },
            {
                "id": "xs-2",
                "title": "Untrusted Input",
                "description": "Search the training catalog for 'laptop' and identify "
                               "which value came from you, the user.",
                "hints": [
                    "Every part of this request is fixed except one — the part you typed.",
                    "It's the 'q' query string parameter.",
                    "Use 'open https://cybershop.training/search?q=laptop'.",
                ],
                "validate": {"type": "web_state", "check": "query_param", "param": "q", "match": "laptop"},
                "xp": 35,
            },
            {
                "id": "xs-3",
                "title": "Reflected XSS",
                "description": "Send the fixed training marker <TRAINING_XSS> to "
                               "/search and observe it reflected — plus a simulated "
                               "browser event.",
                "hints": [
                    ("A reflected value shows up immediately, in the very next "
                     "response — nothing is saved anywhere."),
                    "Set q to <TRAINING_XSS> exactly.",
                    'Use \'open "https://cybershop.training/search?q=<TRAINING_XSS>"\'.',
                ],
                "validate": {"type": "web_state", "check": "reflected_input", "match": "1"},
                "xp": 40,
            },
            {
                "id": "xs-4",
                "title": "Inspect HTTP Request",
                "description": "Capture a search request using the Proxy before it "
                               "reaches the server.",
                "hints": [
                    ("Turn interception on first, the same way you did in the Burp "
                     "Suite mission."),
                    "Use 'intercept on', then make a search request.",
                    "Use 'intercept on', then 'open https://cybershop.training/search?q=keyboard'.",
                ],
                "validate": {"type": "web_state", "check": "request_intercepted", "match": "1"},
                "xp": 40,
            },
            {
                "id": "xs-5",
                "title": "Identify Reflection",
                "description": "Find the exact training marker you submitted inside "
                               "the simulated response body.",
                "hints": [
                    "Compare what you submitted with what the server returned.",
                    "Look for your input inside the response.",
                    "The 'q' parameter's value appears verbatim in the returned HTML.",
                ],
                "validate": {"type": "web_state", "check": "reflected_input", "match": "1"},
                "xp": 35,
            },
            {
                "id": "xs-6",
                "title": "Identify HTML Context",
                "description": "Determine that your reflected value is being rendered "
                               "as HTML text content, not inside an attribute, a script, "
                               "or a URL.",
                "hints": [
                    ("Different places a value can land in a page (text, an attribute, "
                     "a <script> block, a URL) need different defenses."),
                    "Check the X-Sim-XSS-Context header on your last search response.",
                    "It should read 'html_text'.",
                ],
                "validate": {"type": "web_state", "check": "html_context", "match": "html_text"},
                "xp": 40,
            },
            {
                "id": "xs-7",
                "title": "Simulated Execution",
                "description": "Trigger the controlled XSS training marker again and "
                               "observe the 'SIMULATED BROWSER EVENT' panel in the "
                               "response.",
                "hints": [
                    ("This is the same marker from Objective 3 — look at the panel "
                     "beneath the search results."),
                    "It's clearly labeled and states no real JavaScript ever runs.",
                    'Use \'open "https://cybershop.training/search?q=<TRAINING_XSS>"\' again if needed.',
                ],
                "validate": {"type": "web_state", "check": "simulated_xss_event", "match": "1"},
                "xp": 45,
            },
            {
                "id": "xs-8",
                "title": "Stored XSS",
                "description": "Submit the training marker through the vulnerable "
                               "feedback form.",
                "hints": [
                    "Unlike /search, this value isn't reflected immediately — it's saved.",
                    "POST to /feedback with 'name' and 'comment' form fields.",
                    ('Use \'open -X POST -d "name=student&comment=<TRAINING_XSS>" '
                     "https://cybershop.training/feedback'."),
                ],
                "validate": {"type": "web_state", "check": "stored_input", "match": "submitted"},
                "xp": 40,
            },
            {
                "id": "xs-9",
                "title": "Stored Reflection",
                "description": "Open the comments page and observe the previously "
                               "stored training marker — and this time, the simulated "
                               "event fires here, not at submission time.",
                "hints": [
                    "The comment you stored a moment ago should now render on this page.",
                    "Request the comments listing.",
                    "Use 'open https://cybershop.training/comments'.",
                ],
                "validate": {"type": "web_state", "check": "stored_input", "match": "displayed"},
                "xp": 45,
            },
            {
                "id": "xs-10",
                "title": "Reflected vs. Stored",
                "description": "Having triggered both, articulate the difference: "
                               "reflected XSS appears in the immediate response; stored "
                               "XSS is saved and appears in a later, unrelated request.",
                "hints": [
                    "You've now triggered both kinds — no new request needed here.",
                    ("Reflected: request -> response. Stored: request -> storage -> "
                     "a later response."),
                    "If Objectives 3 and 9 are both complete, this one completes too.",
                ],
                "validate": {"type": "web_state", "check": "reflected_vs_stored", "match": "1"},
                "xp": 35,
            },
            {
                "id": "xs-11",
                "title": "DOM XSS",
                "description": "Open the DOM demo page and identify the simulated "
                               "source and sink it describes.",
                "hints": [
                    ("This page describes a client-side flow — no server round-trip "
                     "reflection like /search."),
                    "Request the DOM demo route.",
                    "Use 'open https://cybershop.training/dom-demo'.",
                ],
                "validate": {"type": "web_state", "check": "dom_source", "match": "1"},
                "xp": 40,
            },
            {
                "id": "xs-12",
                "title": "Source/Sink Analysis",
                "description": "Send the training marker as the DOM demo's 'input' "
                               "parameter and observe the simulated DOM sink fire.",
                "hints": [
                    ("The source is the URL parameter; the sink is a simulated DOM "
                     "insertion — connect the two with the training marker."),
                    "Set the 'input' query parameter to <TRAINING_XSS>.",
                    'Use \'open "https://cybershop.training/dom-demo?input=<TRAINING_XSS>"\'.',
                ],
                "validate": {"type": "web_state", "check": "dom_sink", "match": "1"},
                "xp": 45,
            },
            {
                "id": "xs-13",
                "title": "Secure Rendering",
                "description": "Send the exact same training marker to /secure-search "
                               "and observe that it's encoded, not interpreted as HTML.",
                "hints": [
                    ("This endpoint treats your input as data to display, never as "
                     "markup to render."),
                    "Request /secure-search with the same q you used for Objective 3.",
                    ('Use \'open "https://cybershop.training/secure-search?q=<TRAINING_XSS>"\' '
                     "— no simulated event this time."),
                ],
                "validate": {"type": "web_state", "check": "secure_encoding",
                             "endpoint": "/secure-search", "match": "1"},
                "xp": 45,
            },
            {
                "id": "xs-14",
                "title": "Output Encoding",
                "description": "Inspect the secure response body and identify that '<' "
                               "became '&lt;' and '>' became '&gt;'.",
                "hints": [
                    ("HTML escaping doesn't remove the characters — it replaces them "
                     "with a form the browser displays literally instead of parsing."),
                    "Check the response body from Objective 13 for '&lt;' and '&gt;'.",
                    "Both escaped forms should be visible surrounding TRAINING_XSS.",
                ],
                "validate": {"type": "web_state", "check": "html_escaped_observed", "match": "1"},
                "xp": 40,
            },
            {
                "id": "xs-15",
                "title": "Content Security Policy",
                "description": "Inspect the simulated response headers and identify "
                               "the Content-Security-Policy header.",
                "hints": [
                    ("Every response in this training site carries one — check any "
                     "response's headers."),
                    "Use the 'headers' command after any request.",
                    "It should read \"default-src 'self'; script-src 'self'\".",
                ],
                "validate": {"type": "web_state", "check": "header", "header": "Content-Security-Policy",
                             "in": "response", "match": "default-src 'self'; script-src 'self'"},
                "xp": 40,
            },
            {
                "id": "xs-16",
                "title": "Evidence Collection",
                "description": "Before the final investigation, make sure you've "
                               "gathered every kind of evidence: reflected, stored, "
                               "DOM-based, and a secure-endpoint comparison.",
                "hints": [
                    ("Nothing new to send here — just make sure Objectives 3, 9, 12, "
                     "and 13 are all complete."),
                    "If any of those are still incomplete, go back and finish them first.",
                    ("Once reflected, stored, DOM, and the secure endpoint are all "
                     "done, this objective completes automatically."),
                ],
                "validate": {"type": "web_state", "check": "xss_evidence_collected", "match": "1"},
                "xp": 55,
            },
            {
                "id": "xs-17",
                "title": "FINAL INVESTIGATION — The Reflected Comment Box",
                "description": "A bug report says 'our search bar and comments section "
                               "might be exposing us to script injection.' Inspect the "
                               "investigation log, determine whether the input is "
                               "reflected, stored, or reaching a DOM sink, what context "
                               "it renders in, and which defensive control fixes it.",
                "hints": [
                    ("Look closely at entries 2 through 5 — when does the simulated "
                     "event fire, and when doesn't it?"),
                    ("Entry 2 (/search) is reflected — immediate. Entries 3-4 "
                     "(/feedback then /comments) are stored — delayed until "
                     "rendered. Entry 5 (/secure-search) shows the same marker "
                     "safely HTML-escaped — output encoding is the fix."),
                    ('Use \'evidence\' to list the log, then \'inspect 1\' through '
                     "'inspect 5' to read each exchange. Then: "
                     'echo "Conclusion: the search and comments endpoints reflect and '
                     'store the training marker unsafely as HTML - reflected and '
                     'stored XSS. The secure endpoint shows the same marker safely '
                     'HTML-escaped, proving output encoding is the correct defensive '
                     'control." > web/xss-investigation.txt.'),
                ],
                "validate": {"type": "file_contains", "match": "output encoding",
                             "path": "/home/student/web/xss-investigation.txt"},
                "xp": 95,
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
        "web_lab": "xss-investigation",
        "next_mission": "csrf-fundamentals",
    },
    "csrf-fundamentals": {
        "id": "csrf-fundamentals",
        "title": "Cross-Site Request Forgery Fundamentals",
        "description": "Learn how an authenticated browser's automatic cookie "
                       "attachment lets a forged request reach a state-changing "
                       "endpoint without the user's intent — against the same "
                       "simulated training site (CyberShop) and the same Proxy/"
                       "Repeater from YC-035.2. A fictional 'Simulate Request' "
                       "action reproduces the shape of a cross-site forged request "
                       "(an unexpected Origin/Referer header) entirely within your "
                       "own session — it never makes a real network request, never "
                       "touches a second host, and never lets you escape the "
                       "training environment. No real attacker infrastructure, no "
                       "cookie theft, no phishing, no external targets — that's out "
                       "of scope everywhere.",
        "difficulty": "Intermediate",
        "category": "Web Security",
        "xp_total": 750,
        "estimated_minutes": 70,
        "learn": ["What CSRF is", "Why authenticated browsers matter",
                  "Cookies and automatic credential inclusion", "State-changing requests",
                  "Same-origin vs. cross-origin", "The CSRF attack flow",
                  "Why GET should not change state",
                  "CSRF tokens (synchronizer token pattern)", "SameSite cookies",
                  "Origin validation", "Referer validation", "CSRF vs. XSS",
                  "Evidence-based vulnerability confirmation"],
        "objectives": [
            {
                "id": "cs-1",
                "title": "Identify CSRF",
                "description": "Cross-Site Request Forgery tricks an authenticated "
                               "user's own browser into sending a state-changing "
                               "request the user never intended. Check the "
                               "simulated site's overview to see this mission's "
                               "new routes.",
                "hints": [
                    ("The same overview command from earlier missions lists this "
                     "mission's routes too."),
                    "It's a single short word.",
                    "Use 'web'.",
                ],
                "validate": {"type": "command", "match": "web"},
                "xp": 35,
            },
            {
                "id": "cs-2",
                "title": "Authenticated Browser",
                "description": "Log in as the training user, then request a "
                               "protected page and confirm your session cookie is "
                               "attached automatically.",
                "hints": [
                    ("The training credentials are the same ones you've used in "
                     "every mission since Authentication & Sessions."),
                    ('POST username=student&password=training123 to /auth/login, '
                     "then request /account."),
                    ('Use \'open -X POST -d "username=student&password=training123" '
                     "https://cybershop.training/auth/login', then "
                     "'open https://cybershop.training/account'."),
                ],
                "validate": {"type": "web_state", "check": "cookie_sent",
                             "cookie_name": "session_id", "match": "student-session"},
                "xp": 35,
            },
            {
                "id": "cs-3",
                "title": "State-Changing Request",
                "description": "Send a legitimate training transfer and identify "
                               "POST /transfer as a state-changing operation — one "
                               "that actually changes simulated account balances.",
                "hints": [
                    "This endpoint moves simulated training funds between accounts.",
                    "POST to /transfer with 'recipient' and 'amount' form fields.",
                    ('Use \'open -X POST -d "recipient=training-user&amount=100" '
                     "https://cybershop.training/transfer'."),
                ],
                "validate": {"type": "web_state", "check": "state_change_identified", "match": "1"},
                "xp": 40,
            },
            {
                "id": "cs-4",
                "title": "Capture Request",
                "description": "Capture your transfer request using the Proxy "
                               "before it reaches the server.",
                "hints": [
                    ("Turn interception on first, the same way you did in the Burp "
                     "Suite mission."),
                    "Use 'intercept on', then make another transfer request.",
                    ('Use \'intercept on\', then \'open -X POST -d '
                     '"recipient=training-user&amount=50" '
                     "https://cybershop.training/transfer'."),
                ],
                "validate": {"type": "web_state", "check": "request_intercepted", "match": "1"},
                "xp": 40,
            },
            {
                "id": "cs-5",
                "title": "Inspect Credentials",
                "description": "Inspect the captured request and identify the "
                               "session cookie your browser attached automatically "
                               "— the only credential this endpoint checks.",
                "hints": [
                    "Look at the Cookie header on your captured request.",
                    "Forward the request, then check the 'Cookie' request header.",
                    "It should read 'session_id=student-session'.",
                ],
                "validate": {"type": "web_state", "check": "cookie_sent",
                             "cookie_name": "session_id", "match": "student-session"},
                "xp": 35,
            },
            {
                "id": "cs-6",
                "title": "Vulnerable Endpoint",
                "description": "Open the CSRF demo page and read how the "
                               "vulnerable /transfer endpoint trusts the session "
                               "cookie alone, with no check that the request was "
                               "actually intended by the user.",
                "hints": [
                    "There's a dedicated page describing this endpoint.",
                    "Request the CSRF demo route.",
                    "Use 'open https://cybershop.training/csrf-demo'.",
                ],
                "validate": {"type": "web_state", "check": "path", "match": "/csrf-demo"},
                "xp": 35,
            },
            {
                "id": "cs-7",
                "title": "Simulate CSRF",
                "description": "Run the controlled simulated attacker request "
                               "against the vulnerable endpoint — a forged-looking "
                               "request (an attacker Origin/Referer) that your own "
                               "session cookie is still attached to — and observe "
                               "the simulated transfer succeed anyway.",
                "hints": [
                    ("The vulnerable endpoint never looks at Origin or Referer — "
                     "only the session cookie, which your browser sends regardless."),
                    ('Send a POST to /transfer with an Origin header set to '
                     "https://attacker.training."),
                    ('Use \'open -X POST -H "Origin: https://attacker.training" '
                     '-H "Referer: https://attacker.training/" '
                     '-d "recipient=training-user&amount=100" '
                     "https://cybershop.training/transfer'."),
                ],
                "validate": {"type": "web_state", "check": "csrf_simulated", "match": "1"},
                "xp": 55,
            },
            {
                "id": "cs-8",
                "title": "Understand Trust",
                "description": "Having just triggered it, articulate why the "
                               "server accepted that request: it was authenticated "
                               "through a valid session cookie, but the endpoint "
                               "never verified the request was actually intended "
                               "by the user.",
                "hints": [
                    "No new request needed — you already triggered this above.",
                    "Authentication answers 'who is this?', not 'did they mean to do this?'.",
                    "If Objective 7 is complete, this one completes too.",
                ],
                "validate": {"type": "web_state", "check": "csrf_simulated", "match": "1"},
                "xp": 35,
            },
            {
                "id": "cs-9",
                "title": "GET vs. POST",
                "description": "Try requesting /transfer with a plain GET and "
                               "confirm no such route exists — state-changing "
                               "operations in this training site are never "
                               "performed through GET.",
                "hints": [
                    "This is a different request than the ones you've sent so far.",
                    "Request /transfer with no -X flag (defaults to GET).",
                    "Use 'open https://cybershop.training/transfer' — expect 404 Not Found.",
                ],
                "validate": {"type": "web_state", "check": "get_vs_post_identified", "match": "1"},
                "xp": 40,
            },
            {
                "id": "cs-10",
                "title": "CSRF Token",
                "description": "Open the secure transfer page while logged in and "
                               "identify your training CSRF token.",
                "hints": [
                    "This page shows a value that /transfer never required.",
                    "Request the secure transfer route.",
                    "Use 'open https://cybershop.training/secure-transfer'.",
                ],
                "validate": {"type": "web_state", "check": "csrf_token_identified", "match": "1"},
                "xp": 40,
            },
            {
                "id": "cs-11",
                "title": "Missing Token",
                "description": "Send a transfer to /secure-transfer without a "
                               "csrf_token and observe it rejected.",
                "hints": [
                    "Send the same recipient/amount fields as before, but no csrf_token.",
                    "POST to /secure-transfer with only 'recipient' and 'amount'.",
                    ('Use \'open -X POST -d "recipient=training-user&amount=100" '
                     "https://cybershop.training/secure-transfer' — expect 403 Forbidden."),
                ],
                "validate": {"type": "web_state", "check": "missing_token_rejected", "match": "1"},
                "xp": 45,
            },
            {
                "id": "cs-12",
                "title": "Invalid Token",
                "description": "Send a transfer to /secure-transfer with an "
                               "incorrect csrf_token and observe it rejected.",
                "hints": [
                    "Any value that isn't your real training token counts here.",
                    "Add csrf_token=INVALID_TRAINING_TOKEN to your request body.",
                    ('Use \'open -X POST -d '
                     '"recipient=training-user&amount=100&csrf_token=INVALID_TRAINING_TOKEN" '
                     "https://cybershop.training/secure-transfer' — expect 403 Forbidden."),
                ],
                "validate": {"type": "web_state", "check": "invalid_token_rejected", "match": "1"},
                "xp": 45,
            },
            {
                "id": "cs-13",
                "title": "Valid Token",
                "description": "Send a transfer to /secure-transfer with your "
                               "correct training csrf_token from Objective 10 and "
                               "observe it succeed.",
                "hints": [
                    "Use the exact token /secure-transfer showed you earlier.",
                    "Add csrf_token=<your token> to your request body.",
                    ('Use \'open -X POST -d '
                     '"recipient=training-user&amount=100&csrf_token=TRAINING_TOKEN_STUDENT_SESSION" '
                     "https://cybershop.training/secure-transfer' — expect 200 OK."),
                ],
                "validate": {"type": "web_state", "check": "valid_token_accepted", "match": "1"},
                "xp": 45,
            },
            {
                "id": "cs-14",
                "title": "SameSite",
                "description": "Inspect SameSite cookie behavior for all three "
                               "policies — Strict, Lax, and None — and identify "
                               "which one would still let a cross-site forged "
                               "request through.",
                "hints": [
                    "There's a dedicated command for this — try each policy name.",
                    "Use 'samesite strict', 'samesite lax', and 'samesite none'.",
                    ("Only SameSite=None still attaches the cookie to a cross-site "
                     "forged request."),
                ],
                "validate": {"type": "web_state", "check": "samesite_inspected", "match": "3"},
                "xp": 45,
            },
            {
                "id": "cs-15",
                "title": "Origin",
                "description": "Modify the simulated Origin header and observe "
                               "/secure-transfer reject a request from an "
                               "unexpected origin.",
                "hints": [
                    "Set the Origin header to the same attacker value from Objective 7.",
                    "Send a POST to /secure-transfer with Origin: https://attacker.training.",
                    ('Use \'open -X POST -H "Origin: https://attacker.training" '
                     '-d "recipient=training-user&amount=100" '
                     "https://cybershop.training/secure-transfer' — expect 403 Forbidden."),
                ],
                "validate": {"type": "web_state", "check": "origin_rejected", "match": "1"},
                "xp": 45,
            },
            {
                "id": "cs-16",
                "title": "Evidence Collection",
                "description": "Before the final investigation, make sure you've "
                               "gathered every kind of evidence: the simulated "
                               "attack, the token, and the missing/invalid/valid "
                               "token and Origin-rejection results.",
                "hints": [
                    ("Nothing new to send here — just make sure Objectives 7, 10, "
                     "11, 12, 13, and 15 are all complete."),
                    "If any of those are still incomplete, go back and finish them first.",
                    ("Once the attack, the token, and all four rejection/acceptance "
                     "results are done, this objective completes automatically."),
                ],
                "validate": {"type": "web_state", "check": "csrf_evidence_collected", "match": "1"},
                "xp": 55,
            },
            {
                "id": "cs-17",
                "title": "FINAL INVESTIGATION — The Unexpected Transfer",
                "description": "A bug report says 'a training user's balance "
                               "changed after they visited an unrelated page — "
                               "they never clicked transfer.' Inspect the "
                               "investigation log, determine which endpoint let "
                               "this happen, whether authentication alone was "
                               "sufficient, and which defensive control fixes it.",
                "hints": [
                    ("Look closely at entries 2 through 5 — which requests carry "
                     "an attacker Origin/Referer, and which endpoint accepts them "
                     "anyway?"),
                    ("Entry 3 sends a forged-looking request (attacker Origin/"
                     "Referer) to the vulnerable /transfer endpoint and succeeds — "
                     "the session cookie alone was enough. Entry 4 sends the same "
                     "shape to /secure-transfer and is rejected. Entry 5 succeeds "
                     "only once the correct csrf_token is included."),
                    ('Use \'evidence\' to list the log, then \'inspect 1\' through '
                     "'inspect 5' to read each exchange. Then: "
                     'echo "Conclusion: the vulnerable transfer endpoint trusted the '
                     'session cookie alone and accepted a forged-looking cross-site '
                     'request - this is CSRF. The secure endpoint rejected the same '
                     'request shape and only succeeded once the correct anti-csrf '
                     'token was included, proving a synchronizer token is the '
                     'correct defensive control." > web/csrf-investigation.txt.'),
                ],
                "validate": {"type": "file_contains", "match": "anti-csrf token",
                             "path": "/home/student/web/csrf-investigation.txt"},
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
        "web_lab": "csrf-investigation",
        "next_mission": "file-upload-security",
    },
    "file-upload-security": {
        "id": "file-upload-security",
        "title": "File Upload Security Fundamentals",
        "description": "Learn why file uploads are dangerous and why no single "
                       "validation layer — extension, declared MIME type, or "
                       "filename alone — is ever sufficient, against the same "
                       "simulated training site (CyberShop) and the same Proxy/"
                       "Repeater from YC-035.2. There is no real file content "
                       "anywhere: an upload is always a small set of explicit, "
                       "fixed fields (filename, claimed content type, claimed "
                       "size, and a fixed 'signature' label standing in for "
                       "detected magic bytes) — the simulator never reads, "
                       "writes, or executes a real file, never creates a web "
                       "shell, and never lets you escape the training "
                       "environment. No real exploitation tooling, no "
                       "executable payload construction, no arbitrary "
                       "filesystem access — that's out of scope everywhere.",
        "difficulty": "Intermediate",
        "category": "Web Security",
        "xp_total": 800,
        "estimated_minutes": 70,
        "learn": ["Why file uploads are dangerous", "Extension validation",
                  "MIME/content-type validation", "Magic bytes / file signatures",
                  "Content validation", "Filename validation",
                  "Path traversal concept", "File size limits", "Storage location",
                  "Randomized filenames", "Executable content",
                  "Web-accessible upload directories", "Defense-in-depth",
                  "Vulnerable vs. secure upload pipelines",
                  "Evidence-based vulnerability identification"],
        "objectives": [
            {
                "id": "up-1",
                "title": "Upload Basics",
                "description": "Uploading a file follows a flow like any other "
                               "request: your browser sends it, the server "
                               "validates it, then stores it and returns a "
                               "reference. Check the simulated site's overview to "
                               "see this mission's new routes.",
                "hints": [
                    ("The same overview command from earlier missions lists this "
                     "mission's routes too."),
                    "It's a single short word.",
                    "Use 'web'.",
                ],
                "validate": {"type": "command", "match": "web"},
                "xp": 35,
            },
            {
                "id": "up-2",
                "title": "Capture Upload",
                "description": "Log in, then capture an upload request using the "
                               "Proxy before it reaches the server.",
                "hints": [
                    ("Turn interception on first, the same way you did in the "
                     "Burp Suite mission, then upload a training file."),
                    ("Use 'intercept on', then POST to /upload with filename, "
                     "content_type, size, and signature fields."),
                    ('Use \'intercept on\', then \'open -X POST -d '
                     '"filename=avatar.jpg&content_type=image/jpeg&size=24000&signature=JPEG" '
                     "https://cybershop.training/upload'."),
                ],
                "validate": {"type": "web_state", "check": "request_intercepted", "match": "1"},
                "xp": 40,
            },
            {
                "id": "up-3",
                "title": "Multipart Request",
                "description": "Identify that upload requests declare a "
                               "multipart/form-data Content-Type — check your "
                               "captured request's headers.",
                "hints": [
                    "Real file uploads use a distinct request Content-Type.",
                    "Set the Content-Type header explicitly with -H.",
                    ('Use \'open -X POST -H "Content-Type: multipart/form-data; '
                     'boundary=----TrainingBoundary" -d '
                     '"filename=avatar.jpg&content_type=image/jpeg&size=24000&signature=JPEG" '
                     "https://cybershop.training/upload'."),
                ],
                "validate": {"type": "web_state", "check": "multipart_identified", "match": "1"},
                "xp": 40,
            },
            {
                "id": "up-4",
                "title": "Filename",
                "description": "Identify the 'filename' field in your upload "
                               "request body.",
                "hints": [
                    "It's one of the form fields in the request body.",
                    "Check the 'filename' field's value.",
                    "It should read 'avatar.jpg'.",
                ],
                "validate": {"type": "web_state", "check": "body_field", "field": "filename",
                             "in": "request", "match": "avatar.jpg"},
                "xp": 35,
            },
            {
                "id": "up-5",
                "title": "Extension",
                "description": "Identify the file extension the server detected "
                               "from your uploaded filename.",
                "hints": [
                    "Forward your intercepted request first, if you haven't already.",
                    "Check the X-Sim-Upload-Extension response header.",
                    "It should read '.jpg'.",
                ],
                "validate": {"type": "web_state", "check": "extension_identified", "match": ".jpg"},
                "xp": 35,
            },
            {
                "id": "up-6",
                "title": "MIME Type",
                "description": "Identify the declared Content-Type of your "
                               "uploaded file.",
                "hints": [
                    "This is the 'content_type' field you sent, echoed back.",
                    "Check the X-Sim-Upload-Mime response header.",
                    "It should read 'image/jpeg'.",
                ],
                "validate": {"type": "web_state", "check": "header", "header": "X-Sim-Upload-Mime",
                             "in": "response", "match": "image/jpeg"},
                "xp": 40,
            },
            {
                "id": "up-7",
                "title": "Extension Validation",
                "description": "Demonstrate why extension validation alone is "
                               "insufficient: upload the provided controlled "
                               "training mismatch (a '.jpg' filename whose "
                               "content doesn't match) to the vulnerable "
                               "endpoint and observe it still gets accepted.",
                "hints": [
                    ("The training file 'mismatched.jpg' claims one thing but "
                     "its content signature says another."),
                    "POST it to /upload with content_type=text/plain and signature=TEXT.",
                    ('Use \'open -X POST -H "Content-Type: multipart/form-data; '
                     'boundary=----TrainingBoundary" -d '
                     '"filename=mismatched.jpg&content_type=text/plain&size=2000&signature=TEXT" '
                     "https://cybershop.training/upload' — expect 200 OK anyway."),
                ],
                "validate": {"type": "web_state", "check": "content_validation_tested", "match": "1"},
                "xp": 50,
            },
            {
                "id": "up-8",
                "title": "MIME Validation",
                "description": "The same request you just sent also proves MIME "
                               "type alone is insufficient: the vulnerable "
                               "endpoint never even inspected the declared "
                               "Content-Type before accepting the file.",
                "hints": [
                    "No new request needed — you already triggered this above.",
                    "The vulnerable endpoint only ever checks the extension.",
                    "If Objective 7 is complete, this one completes too.",
                ],
                "validate": {"type": "web_state", "check": "content_validation_tested", "match": "1"},
                "xp": 35,
            },
            {
                "id": "up-9",
                "title": "File Signature",
                "description": "Inspect the simulated magic-bytes/signature the "
                               "server detected for one of your uploads.",
                "hints": [
                    "Every upload response carries this, whether accepted or not.",
                    "Check the X-Sim-Upload-Signature response header.",
                    "Use 'headers' right after any upload request.",
                ],
                "validate": {"type": "web_state", "check": "signature_inspected", "match": "1"},
                "xp": 40,
            },
            {
                "id": "up-10",
                "title": "Content Validation",
                "description": "Send the exact same mismatched training file to "
                               "the secure endpoint and confirm the actual "
                               "content — not just the filename — is what "
                               "determines whether it's rejected.",
                "hints": [
                    "Same fields as Objective 7, different endpoint.",
                    "POST the mismatched file to /secure-upload instead of /upload.",
                    ('Use \'open -X POST -H "Content-Type: multipart/form-data; '
                     'boundary=----TrainingBoundary" -d '
                     '"filename=mismatched.jpg&content_type=text/plain&size=2000&signature=TEXT" '
                     "https://cybershop.training/secure-upload' — expect it rejected this time."),
                ],
                "validate": {"type": "web_state", "check": "content_mismatch_confirmed", "match": "1"},
                "xp": 50,
            },
            {
                "id": "up-11",
                "title": "Size Limit",
                "description": "Upload a file exceeding the simulated 2 MB size "
                               "limit and observe it rejected.",
                "hints": [
                    "The training file 'oversized.jpg' is well over the limit.",
                    "Set size=3000000 in your upload request.",
                    ('Use \'open -X POST -H "Content-Type: multipart/form-data; '
                     'boundary=----TrainingBoundary" -d '
                     '"filename=oversized.jpg&content_type=image/jpeg&size=3000000&signature=JPEG" '
                     "https://cybershop.training/upload' — expect 413 Payload Too Large."),
                ],
                "validate": {"type": "web_state", "check": "size_limit_tested", "match": "1"},
                "xp": 45,
            },
            {
                "id": "up-12",
                "title": "Filename Security",
                "description": "Test a controlled path-traversal-shaped filename "
                               "against the secure endpoint and observe it "
                               "blocked.",
                "hints": [
                    "Prefix the filename with a directory traversal sequence.",
                    "Set filename=../avatar.jpg and POST to /secure-upload.",
                    ('Use \'open -X POST -H "Content-Type: multipart/form-data; '
                     'boundary=----TrainingBoundary" -d '
                     '"filename=../avatar.jpg&content_type=image/jpeg&size=24000&signature=JPEG" '
                     "https://cybershop.training/secure-upload' — expect 403 Forbidden."),
                ],
                "validate": {"type": "web_state", "check": "path_traversal_blocked", "match": "1"},
                "xp": 50,
            },
            {
                "id": "up-13",
                "title": "Storage",
                "description": "Successfully upload a valid training file "
                               "through the secure endpoint and compare its "
                               "storage behavior — private, not web-accessible "
                               "— with the vulnerable endpoint's earlier result.",
                "hints": [
                    "Send the same, valid avatar.jpg fields you used before.",
                    "POST to /secure-upload with the correct, matching fields.",
                    ('Use \'open -X POST -H "Content-Type: multipart/form-data; '
                     'boundary=----TrainingBoundary" -d '
                     '"filename=avatar.jpg&content_type=image/jpeg&size=24000&signature=JPEG" '
                     "https://cybershop.training/secure-upload' — expect 200 OK."),
                ],
                "validate": {"type": "web_state", "check": "storage_inspected", "match": "1"},
                "xp": 45,
            },
            {
                "id": "up-14",
                "title": "Randomized Filename",
                "description": "Observe the secure endpoint's server-generated, "
                               "randomized stored filename — different from the "
                               "original filename you uploaded.",
                "hints": [
                    "No new request needed — check the response from Objective 13.",
                    "Check the X-Sim-Upload-Stored-Name response header.",
                    "It should not read 'avatar.jpg'.",
                ],
                "validate": {"type": "web_state", "check": "random_filename_observed", "match": "1"},
                "xp": 40,
            },
            {
                "id": "up-15",
                "title": "Executable Content",
                "description": "Test the safe 'training-executable-marker' file "
                               "against the secure endpoint and observe it "
                               "blocked.",
                "hints": [
                    ("The training file 'shell.jpg' looks like an image by "
                     "extension, but its signature says otherwise."),
                    "Set signature=EXECUTABLE and POST to /secure-upload.",
                    ('Use \'open -X POST -H "Content-Type: multipart/form-data; '
                     'boundary=----TrainingBoundary" -d '
                     '"filename=shell.jpg&content_type=image/jpeg&size=8000&signature=EXECUTABLE" '
                     "https://cybershop.training/secure-upload' — expect 403 Forbidden."),
                ],
                "validate": {"type": "web_state", "check": "executable_marker_blocked", "match": "1"},
                "xp": 50,
            },
            {
                "id": "up-16",
                "title": "Vulnerable vs. Secure",
                "description": "Having successfully completed an upload through "
                               "both endpoints, compare the two pipelines: one "
                               "checks a single layer, the other applies several "
                               "independent controls.",
                "hints": [
                    "No new request needed here.",
                    "You've already completed uploads through both /upload and /secure-upload.",
                    "If Objectives 2 and 13 are both complete, this one completes too.",
                ],
                "validate": {"type": "web_state", "check": "secure_pipeline_compared", "match": "1"},
                "xp": 50,
            },
            {
                "id": "up-17",
                "title": "Evidence Collection",
                "description": "Before the final investigation, make sure you've "
                               "gathered every kind of evidence: a content "
                               "mismatch, a signature inspection, the size "
                               "limit, path traversal, executable blocking, and "
                               "both pipelines tested.",
                "hints": [
                    ("Nothing new to send here — just make sure Objectives 7, 9, "
                     "11, 12, 15, 2, and 13 are all complete."),
                    "If any of those are still incomplete, go back and finish them first.",
                    ("Once every kind of evidence above is collected, this "
                     "objective completes automatically."),
                ],
                "validate": {"type": "web_state", "check": "upload_evidence_collected", "match": "1"},
                "xp": 55,
            },
            {
                "id": "up-18",
                "title": "FINAL INVESTIGATION — The Public Profile Picture",
                "description": "A bug report says 'someone uploaded a profile "
                               "picture that isn't actually an image, and it's "
                               "sitting in a public folder.' Inspect the "
                               "investigation log, determine which validation "
                               "layers are present or missing, whether "
                               "executable content can reach storage, whether "
                               "uploads are web-accessible, and which defenses "
                               "should be implemented.",
                "hints": [
                    ("Look closely at entries 2 through 6 — which file reaches "
                     "storage despite not being a real image, and which pipeline "
                     "catches it?"),
                    ("Entry 3 uploads a disguised executable ('shell.jpg') "
                     "through the vulnerable, extension-only endpoint and it "
                     "succeeds. Entry 4 sends the same file to the secure "
                     "endpoint and it's blocked by content-signature "
                     "validation. Entry 5 shows the shared size limit reject an "
                     "oversized file. Entry 6 shows a normal file accepted "
                     "securely, with a randomized, non-web-accessible stored "
                     "name."),
                    ('Use \'evidence\' to list the log, then \'inspect 1\' through '
                     "'inspect 6' to read each exchange. Then: "
                     'echo "Conclusion: the vulnerable endpoint validated only the '
                     "file extension, letting a disguised executable file reach "
                     "storage under its original, web-accessible name. The secure "
                     "endpoint applied multiple independent controls - size, "
                     "extension, filename normalization, declared MIME, and "
                     "content signature - and stored the valid file under a "
                     "randomized, private name instead. No single layer is "
                     'enough; this is defense in depth." > '
                     "web/upload-investigation.txt."),
                ],
                "validate": {"type": "file_contains", "match": "defense in depth",
                             "path": "/home/student/web/upload-investigation.txt"},
                "xp": 65,
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
        "web_lab": "upload-investigation",
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
