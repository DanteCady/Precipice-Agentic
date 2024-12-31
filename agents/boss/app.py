from flask import Flask, request, jsonify
import redis
import json
import time
import logging
from threading import Thread
from psycopg2.extras import RealDictCursor
from shared.communication import send_message, format_message
from shared.db_utils import get_db_connection, init_db
from openai import OpenAI

app = Flask(__name__)

# Environment variables (set these in your environment)
REDIS_HOST = "redis"
POSTGRES_HOST = "postgres"
OPENAI_API_KEY = ""  # Replace with your OpenAI API key
OpenAI.api_key = OPENAI_API_KEY

# Redis connection
redis_client = redis.StrictRedis(host=REDIS_HOST, port=6379, decode_responses=True)

# Logging setup
logging.basicConfig(level=logging.INFO)

# OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)


def save_project_to_db(user_id, description, tasks):
    """
    Save project details to PostgreSQL.
    """
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
            INSERT INTO projects (user_id, description, tasks)
            VALUES (%s, %s, %s)
            RETURNING id
            """, (user_id, description, json.dumps(tasks)))
            project_id = cursor.fetchone()["id"]
            conn.commit()
            return project_id
    except Exception as e:
        logging.error(f"Failed to save project to database: {e}")
        raise
    finally:
        if conn:
            conn.close()


@app.route("/talk", methods=["POST"])
def talk_to_boss():
    """
    Generate a project plan dynamically using GPT and save it to Redis and PostgreSQL.
    """
    user_input = request.json.get("message", "")
    user_id = request.json.get("user_id", "default_user")

    if not user_input:
        return jsonify({"error": "Message is required."}), 400

    try:
        # Generate project description with OpenAI
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a project manager for software development."},
                {"role": "user", "content": f"Create a project plan for: {user_input}"}
            ]
        )
        project_description = response.choices[0].message.content

        # Generate tasks with OpenAI
        task_response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": """You are an experienced software architect. 
                Create a balanced mix of frontend and backend tasks.
                Always respond with a valid JSON array of task objects. 
                Each task object should have the fields: 
                - "task": Clear task description prefixed with [Frontend] or [Backend]
                - "priority": 1-10
                - "estimated_hours": estimated hours
                - "dependencies": array of task names that must be completed first
                
                Example:
                [
                    {"task": "[Backend] Set up database schema", "priority": 1, "estimated_hours": 4, "dependencies": []},
                    {"task": "[Frontend] Create login UI", "priority": 2, "estimated_hours": 3, "dependencies": []}
                ]"""},
                {"role": "user", "content": f"Generate a list of tasks for this project: {project_description}. Include both frontend and backend tasks. Respond only with the JSON array."}
            ]
        )
        tasks_content = task_response.choices[0].message.content

        # Parse tasks
        tasks = json.loads(tasks_content)
        
        # Create a mapping of task names to IDs
        task_name_to_id = {}
        for idx, task in enumerate(tasks):
            task_id = idx + 1
            task_name_to_id[task["task"]] = task_id
            task["status"] = "pending"
            task["task_id"] = task_id
            
            # Convert string dependencies to task IDs
            if "dependencies" in task:
                task["dependencies"] = [
                    task_name_to_id.get(dep, dep) 
                    for dep in task["dependencies"]
                ]

        # Save project to PostgreSQL and Redis
        project_id = save_project_to_db(user_id, project_description, tasks)
        project_plan = {
            "project_id": project_id,
            "user_id": user_id,
            "description": project_description,
            "tasks": tasks,
            "status": "in_progress"
        }
        redis_client.set(f"project:{project_id}", json.dumps(project_plan))

        return jsonify({
            "response": "Project plan created successfully",
            "project_id": project_id,
            "description": project_description,
            "tasks": tasks
        })

    except Exception as e:
        logging.error(f"Failed to generate project plan: {e}")
        return jsonify({"error": f"Failed to generate project plan: {str(e)}"}), 500


@app.route("/task_complete", methods=["POST"])
def task_complete():
    """
    Update the status of a completed task.
    """
    data = request.json
    project_id = data.get("project_id")
    task_id = data.get("task_id")
    status = data.get("status", "completed")

    if not project_id or not task_id:
        return jsonify({"error": "Project ID and Task ID are required."}), 400

    try:
        # Fetch project details
        project_plan = json.loads(redis_client.get(f"project:{project_id}"))
        if not project_plan:
            raise ValueError(f"No project found with ID {project_id}.")

        # Update task status
        task_found = False
        for task in project_plan["tasks"]:
            if task["task_id"] == task_id:
                task["status"] = status
                task_found = True
                break

        if not task_found:
            raise ValueError(f"Task ID {task_id} not found in project {project_id}.")

        # Save updated project to Redis
        redis_client.set(f"project:{project_id}", json.dumps(project_plan))

        return jsonify({"response": f"Task {task_id} status updated to {status}"})

    except Exception as e:
        logging.error(f"Failed to update task {task_id}: {e}")
        return jsonify({"error": f"Failed to update task: {str(e)}"}), 500


def task_delegation_worker():
    """
    Background worker to monitor and delegate tasks automatically.
    """
    while True:
        try:
            keys = redis_client.keys("project:*")
            for key in keys:
                project_plan = json.loads(redis_client.get(key))
                tasks = project_plan.get("tasks", [])

                for task in tasks:
                    if task["status"] == "pending" and all(
                        any(dep["task_id"] == dep_id and dep["status"] == "completed" 
                            for dep in project_plan["tasks"])
                        for dep_id in task.get("dependencies", [])
                    ):
                        task_lower = task["task"].lower()
                        developer = None
                        
                        if "[frontend]" in task_lower:
                            developer = "dev_1"
                        elif "[backend]" in task_lower:
                            developer = "dev_2"
                        else:
                            developer = "dev_1" if task["task_id"] % 2 == 0 else "dev_2"

                        if task.get("developer"):
                            continue

                        task["status"] = "in_progress"
                        task["developer"] = developer
                        redis_client.publish(f"tasks:{developer}", json.dumps(task))
                        logging.info(f"Task {task['task_id']}: {task['task']} assigned to {developer}")

                redis_client.set(key, json.dumps(project_plan))

        except Exception as e:
            logging.error(f"Task delegation worker encountered an error: {str(e)}")

        time.sleep(5)


if __name__ == "__main__":
    time.sleep(5)  # Wait for services to be ready
    logging.info("Initializing database...")
    init_db()
    logging.info("Starting Boss agent...")

    Thread(target=task_delegation_worker, daemon=True).start()

    app.run(host="0.0.0.0", port=8000)
