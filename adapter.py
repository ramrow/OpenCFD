# app.py
from flask import Flask, request, jsonify
import subprocess
import os

app = Flask(__name__)

USER_REQ_PATH = "./user_requirement.txt"
OUTPUT_DIR = "./output"


@app.route("/run_foambench", methods=["POST"])
def run_foambench():
    # 1. Get user requirement from request body (JSON or form)
    if request.is_json:
        data = request.get_json()
        user_requirement = data.get("user_requirement", "")
    else:
        user_requirement = request.form.get("user_requirement", "")

    if not user_requirement:
        return jsonify({"error": "user_requirement is required"}), 400

    # 2. Overwrite user_requirement.txt
    try:
        with open(USER_REQ_PATH, "w", encoding="utf-8") as f:
            f.write(user_requirement)
    except Exception as e:
        return jsonify({"error": f"Failed to write user_requirement.txt: {e}"}), 500

    # 3. Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 4. Run the foambench command
    cmd = [
        "python",
        "foambench_main.py",
        "--output",
        OUTPUT_DIR,
        "--prompt_path",
        USER_REQ_PATH,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,  # don't raise on non-zero return code; we handle it
        )
    except Exception as e:
        return jsonify({"error": f"Failed to run foambench_main.py: {e}"}), 500

    # Optional: print to backend terminal for debugging
    print("\n===== foambench_main.py OUTPUT =====")
    print("Return code:", result.returncode)
    print("\n--- STDOUT ---")
    print(result.stdout)
    print("\n--- STDERR ---")
    print(result.stderr)
    print("=====================================\n")

    # 5. Return the results, including output_dir
    return jsonify(
        {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "output_dir": os.path.abspath(OUTPUT_DIR),
        }
    ), 500


if __name__ == "__main__":
    # For local development only
    app.run(host="0.0.0.0", port=7860, debug=True)