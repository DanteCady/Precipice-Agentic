from flask import Flask, request, jsonify
from shared.communication import send_message, format_message
import redis
import json
import time
from threading import Thread

app = Flask(__name__)

# Redis connection
REDIS_HOST = "redis"
redis_client = redis.StrictRedis(host=REDIS_HOST, port=6379, decode_responses=True)

# Task queue and collaboration log
tasks_in_progress = []
completed_tasks = []
collaboration_log = []

def task_listener():
    """
    Listen to Redis channels for task assignments.
    """
    pubsub = redis_client.pubsub()
    pubsub.subscribe("tasks:dev_2")  

    for message in pubsub.listen():
        if message["type"] == "message":
            task = json.loads(message["data"])
            process_task(task)

def process_task(task):
    """
    Process a received task.
    """
    task_id = len(tasks_in_progress) + 1
    task["task_id"] = task_id
    task["status"] = "in_progress"
    tasks_in_progress.append(task)

    # Simulate task processing time
    estimated_time = task.get("estimated_hours", 1) * 0.01
    time.sleep(estimated_time)
    task["status"] = "completed"
    completed_tasks.append(task)
    tasks_in_progress.remove(task)

    # Notify the Boss of task completion
    task_complete_payload = {
        "project_id": task.get("project_id"),
        "task_id": task_id,
        "status": "completed"
    }
    redis_client.publish("task_updates", json.dumps(task_complete_payload))  # Notify Boss

@app.route("/collaborate", methods=["POST"])
def collaborate():
    """
    Handle messages from peer agents.
    """
    message = request.json.get("message")
    if not message:
        return jsonify({"error": "Message content is required"}), 400

    collaboration_log.append(message)
    response = format_message("dev_1", f"Acknowledged: {message}")
    return jsonify(response)

@app.route("/status", methods=["GET"])
def report_status():
    """
    Report current task status and collaboration updates.
    """
    return jsonify({
        "status": "In progress" if tasks_in_progress else "Idle",
        "tasks_in_progress": tasks_in_progress,
        "completed_tasks": completed_tasks,
        "collaborations": collaboration_log
    })

if __name__ == "__main__":
    # Start Redis task listener in a separate thread
    Thread(target=task_listener, daemon=True).start()

    # Start the Flask app
    app.run(host="0.0.0.0", port=8002) 
