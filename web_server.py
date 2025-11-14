"""
Web server for managing the LiveKit agent
Provides a simple web interface to start/stop the agent
"""

import os
import subprocess
import signal
import logging
from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
import threading
import time

app = Flask(__name__, static_folder='.')
CORS(app)

logger = logging.getLogger("web-server")
logger.setLevel(logging.INFO)

# Global process management
agent_process = None
agent_thread = None
agent_status = {
    "running": False,
    "pid": None,
    "start_time": None,
    "logs": []
}


def run_agent():
    """Run the agent in a separate thread"""
    global agent_process, agent_status
    
    try:
        logger.info("Starting agent process...")
        agent_status["running"] = True
        agent_status["start_time"] = time.time()
        
        # Determine Python executable (prefer venv if available)
        python_exe = "python"
        if os.path.exists(".venv/bin/python"):
            python_exe = ".venv/bin/python"
        elif os.path.exists("venv/bin/python"):
            python_exe = "venv/bin/python"
        
        # Start the agent process in dev mode for interactive testing
        # Pass environment variables to ensure .env is loaded
        env = os.environ.copy()
        agent_process = subprocess.Popen(
            [python_exe, "assistant.py", "dev"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            env=env,
            cwd=os.getcwd()
        )
        
        agent_status["pid"] = agent_process.pid
        add_log("Agent process started (PID: {})".format(agent_process.pid), "success")
        
        # Read output line by line
        for line in iter(agent_process.stdout.readline, ''):
            if line:
                add_log(line.strip(), "info")
        
        # Process ended
        agent_process.wait()
        agent_status["running"] = False
        agent_status["pid"] = None
        add_log("Agent process ended", "info")
        
    except Exception as e:
        logger.error(f"Error running agent: {e}")
        agent_status["running"] = False
        agent_status["pid"] = None
        add_log(f"Error: {str(e)}", "error")


def add_log(message, level="info"):
    """Add a log entry"""
    log_entry = {
        "time": time.strftime("%H:%M:%S"),
        "message": message,
        "level": level
    }
    agent_status["logs"].append(log_entry)
    # Keep only last 100 logs
    if len(agent_status["logs"]) > 100:
        agent_status["logs"] = agent_status["logs"][-100:]


@app.route('/')
def index():
    """Serve the HTML interface"""
    return send_from_directory('.', 'index.html')


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get agent status"""
    uptime = None
    if agent_status["running"] and agent_status["start_time"]:
        uptime_seconds = int(time.time() - agent_status["start_time"])
        minutes = uptime_seconds // 60
        seconds = uptime_seconds % 60
        uptime = f"{minutes}m {seconds}s"
    
    return jsonify({
        "running": agent_status["running"],
        "pid": agent_status["pid"],
        "uptime": uptime,
        "logs": agent_status["logs"][-20:]  # Last 20 logs
    })


@app.route('/api/start', methods=['POST'])
def start_agent():
    """Start the agent"""
    global agent_thread, agent_process
    
    if agent_status["running"]:
        return jsonify({"success": False, "error": "Agent is already running"})
    
    try:
        # Start agent in a separate thread
        agent_thread = threading.Thread(target=run_agent, daemon=True)
        agent_thread.start()
        
        # Wait a moment to check if it started successfully
        time.sleep(1)
        
        if agent_status["running"]:
            return jsonify({"success": True, "message": "Agent started successfully"})
        else:
            return jsonify({"success": False, "error": "Failed to start agent"})
            
    except Exception as e:
        logger.error(f"Error starting agent: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/stop', methods=['POST'])
def stop_agent():
    """Stop the agent"""
    global agent_process, agent_thread
    
    if not agent_status["running"]:
        return jsonify({"success": False, "error": "Agent is not running"})
    
    try:
        if agent_process:
            agent_process.terminate()
            # Wait up to 5 seconds for graceful shutdown
            try:
                agent_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't stop
                agent_process.kill()
                agent_process.wait()
            
            agent_process = None
        
        agent_status["running"] = False
        agent_status["pid"] = None
        agent_status["start_time"] = None
        
        add_log("Agent stopped by user", "info")
        
        return jsonify({"success": True, "message": "Agent stopped successfully"})
        
    except Exception as e:
        logger.error(f"Error stopping agent: {e}")
        return jsonify({"success": False, "error": str(e)})


if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Catalina Marketing Printer Support Agent - Web Interface")
    print("="*60)
    print("\n📡 Starting web server on http://localhost:5001")
    print("🌐 Open your browser and navigate to: http://localhost:5001")
    print("\n⚠️  Make sure your .env file is configured with:")
    print("   - LIVEKIT_URL")
    print("   - LIVEKIT_API_KEY")
    print("   - LIVEKIT_API_SECRET")
    print("   - OPENAI_API_KEY")
    print("   - DEEPGRAM_API_KEY")
    print("\n" + "="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5001, debug=False)

