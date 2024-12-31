PrecipiceTech-Agentic

Overview

PrecipiceTech-Agentic is a multi-agent system designed to simulate a collaborative environment where an orchestrator agent (Boss) communicates with two developer agents (Developer 1 and Developer 2) to build software autonomously. The Boss receives user input, delegates tasks to developers, and monitors their progress. The developers collaborate with each other to complete tasks.

Project Structure

└── 📁PrecipiceTech-Agentic
    └── 📁agents
        └── 📁boss
            └── app.py           # Main script for the Boss agent
            └── Dockerfile       # Docker setup for the Boss agent
            └── requirements.txt # Dependencies for the Boss agent
        └── 📁developers
            └── 📁developer-1
                └── app.py           # Main script for Developer 1
                └── Dockerfile       # Docker setup for Developer 1
                └── requirements.txt # Dependencies for Developer 1
            └── 📁developer-2
                └── app.py           # Main script for Developer 2
                └── Dockerfile       # Docker setup for Developer 2
                └── requirements.txt # Dependencies for Developer 2
    └── 📁shared
        └── communication.py     # Shared utility functions for communication
    └── docker-compose.yml        # Docker Compose setup for multi-agent orchestration
    └── README.md                 # Project documentation

Getting Started

Prerequisites

Docker: Install Docker for containerization.

Docker Compose: Ensure Docker Compose is available.

Setup Instructions

Clone the Repository:

git clone <repository-url>
cd PrecipiceTech-Agentic

Build the Containers:

docker-compose build

Start the Services:

docker-compose up

Access the Services:

Boss API: http://localhost:8000

Developer 1 API: http://localhost:8001

Developer 2 API: http://localhost:8002

Interacting with the System

Talk to the Boss

Send a task to the Boss agent:

curl -X POST -H "Content-Type: application/json" \
     -d '{"message": "Create a web application"}' \
     http://localhost:8000/talk

Delegate Tasks

Ask the Boss to delegate tasks to the developers:

curl -X POST http://localhost:8000/delegate_tasks

Check Developer Progress

Fetch the progress of tasks from the Boss:

curl -X GET http://localhost:8000/get_progress

System Architecture

Boss:

Receives high-level instructions from the user.

Creates a project plan and delegates tasks to the developers.

Monitors the developers' progress and resolves conflicts.

Developer 1:

Handles frontend-related tasks.

Reports progress to the Boss.

Developer 2:

Handles backend-related tasks.

Reports progress to the Boss.

Shared Communication:

Provides utility functions for inter-agent communication.

Technologies Used

Programming Language: Python 3.10

Web Framework: Flask

Containerization: Docker

Orchestration: Docker Compose

Future Enhancements

Add memory and reasoning capabilities to each agent.

Introduce dynamic task reassignment based on agent performance.

Build a frontend UI to interact with the Boss.

Add AI-powered features for generating and validating code autonomously.

License

This project is licensed under the MIT License. See the LICENSE file for details.

Contact

For questions or collaboration, contact [your-email@example.com].