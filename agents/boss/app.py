from flask import Flask, request, jsonify
import redis
import json
import time
import logging
from threading import Thread
from psycopg2 import connect, sql
from psycopg2.extras import RealDictCursor
from shared.communication import send_message, format_message
from shared.db_utils import get_db_connection, init_db
from openai import OpenAI

app = Flask(__name__)

# Environment variables (set these in your environment)
REDIS_HOST = "redis"
POSTGRES_HOST = "postgres"
OPENAI_API_KEY = "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"  # Replace with your OpenAI API key
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
    Receive input from the user and dynamically generate a project plan using GPT.
    Save the project in PostgreSQL and cache it in Redis.
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

        # Generate tasks with explicit JSON formatting instructions
        task_response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": """You are an experienced software architect. 
                Always respond with a valid JSON array of task objects. 
                Each task object should have these fields:
                - "task": string describing the task
                - "priority": number from 1-5
                - "estimated_hours": number
                - "dependencies": array of task numbers that must be completed first
                Example format:
                [
                    {
                        "task": "Set up basic project structure",
                        "priority": 1,
                        "estimated_hours": 2,
                        "dependencies": []
                    },
                    {
                        "task": "Implement user authentication",
                        "priority": 2,
                        "estimated_hours": 4,
                        "dependencies": [1]
                    }
                ]"""},
                {"role": "user", "content": f"Generate a list of tasks for this project: {project_description}. Respond only with the JSON array, no additional text."}
            ]
        )
        tasks_content = task_response.choices[0].message.content

        # Parse tasks from GPT output
        tasks = json.loads(tasks_content)
        for task in tasks:
            task["status"] = "pending"

        # Save the project to PostgreSQL
        project_id = save_project_to_db(user_id, project_description, tasks)

        # Cache the project in Redis
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
        return jsonify({"error": "Project ID and Task ID are required"}), 400

    try:
        # Fetch project details
        project_plan = redis_client.get(f"project:{project_id}")
        if not project_plan:
            conn = get_db_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
                project_plan = cursor.fetchone()
            if not project_plan:
                return jsonify({"error": f"No project found with ID {project_id}."}), 404

        project_plan = json.loads(project_plan)

        # Update task status
        for task in project_plan.get("tasks", []):
            if task.get("task_id") == task_id:
                task["status"] = status
                break

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
                delegation_status = project_plan.get("delegation_status", [])

                # Check for pending tasks
                for task in tasks:
                    if task["status"] == "pending" and all(
                        dep["status"] == "completed" for dep in task.get("dependencies", [])
                    ):
                        # Decide which developer to assign the task to
                        developer = "dev_1" if "frontend" in task["task"].lower() else "dev_2"
                        dev_channel = f"tasks:{developer}"

                        # Publish task to developer's Redis channel
                        task["status"] = "in_progress"
                        redis_client.publish(dev_channel, json.dumps(task))
                        delegation_status.append({"task": task, "developer": developer, "status": "delegated"})

                # Update project plan
                project_plan["delegation_status"] = delegation_status
                redis_client.set(key, json.dumps(project_plan))

        except Exception as e:
            logging.error(f"Task delegation worker encountered an error: {e}")

        time.sleep(5)  # Check every 5 seconds


if __name__ == "__main__":
    # Wait for dependencies to be ready
    time.sleep(5)  # Allow Redis and PostgreSQL to start
    logging.info("Initializing database...")
    init_db()
    logging.info("Starting Boss agent...")

    # Start the delegation worker
    Thread(target=task_delegation_worker, daemon=True).start()

    app.run(host="0.0.0.0", port=8000)
