# # app_chainlit.py (or web.py)
# import json
# import aiohttp
# import chainlit as cl

# ADAPTER_URL = "http://localhost:7860/run_foambench"


# async def call_adapter(user_requirement: str) -> dict:
#     """
#     Send the user requirement to the Flask adapter and return the JSON response.
#     """
#     payload = {"user_requirement": user_requirement}

#     try:
#         async with aiohttp.ClientSession() as session:
#             async with session.post(ADAPTER_URL, json=payload) as resp:
#                 # Try to parse JSON; if it fails, capture text
#                 try:
#                     data = await resp.json()
#                 except Exception:
#                     text = await resp.text()
#                     data = {
#                         "error": "Adapter did not return valid JSON",
#                         "raw_response": text,
#                         "status": resp.status,
#                     }
#                 return data
#     except Exception as e:
#         return {"error": f"Failed to connect to adapter at {ADAPTER_URL}: {e}"}


# @cl.on_chat_start
# async def on_chat_start():
#     """
#     Just show a welcome message. No LLM, just a UI wrapper over the adapter.
#     """
#     await cl.Message(
#         content=(
#             "🧩 Frontend is ready.\n\n"
#             "Anything you type will be sent as `user_requirement` to:\n"
#             f"`POST {ADAPTER_URL}`."
#         )
#     ).send()


# @cl.on_message
# async def on_message(message: cl.Message):
#     """
#     For each user message:
#     - Forward content as `user_requirement` to the adapter.
#     - Display the adapter's JSON response nicely in the UI.
#     """
#     user_text = message.content

#     # ✅ Create the message object first, then send it
#     running_msg = cl.Message(content="⏳ Sending to backend...")
#     await running_msg.send()

#     adapter_result = await call_adapter(user_text)
#     print(adapter_result)
#     # === Robust handling of adapter responses ===
#     if (
#         isinstance(adapter_result, dict)
#         and "returncode" in adapter_result
#         and ("stdout" in adapter_result or "stderr" in adapter_result)
#     ):
#         rc = adapter_result.get("returncode")

#         # Use "or ''" so None becomes empty string and .strip() is safe
#         # stdout = adapter_result.get("stdout") or ""
#         # stderr = adapter_result.get("stderr") or ""
#         content = adapter_result.get("output_dir") or ""

#         # summary_parts = [f"✅ **Return code:** `{rc}`"]

#         # if stdout.strip():
#         #     summary_parts.append(f"\n📤 **STDOUT:**\n```text\n{stdout.strip()}\n```")
#         # if stderr.strip():
#         #     summary_parts.append(f"\n⚠️ **STDERR:**\n```text\n{stderr.strip()}\n```")

#         # content = "\n".join(summary_parts)
#     else:
#         # Fallback: dump whatever JSON we got
#         pretty = json.dumps(adapter_result, indent=2, ensure_ascii=False)
#         content = f"📡 **Adapter response:**\n```json\n{pretty}\n```"

#     # ✅ Now running_msg is a real Message object, so update works
#     # await running_msg.Message(content=content)
#     await cl.Message(content=content).send()


import os
import json
from typing import Dict, Any

import httpx
import chainlit as cl

# Adjust this if your backend is on a different host/port/path
BACKEND_URL = "http://localhost:7860/run_foambench"


async def call_backend(user_requirement: str) -> Dict[str, Any]:
    """
    Send user_requirement to the backend and return the parsed JSON response.

    Expects the backend to return something like:
    {
        "returncode": int,
        "stdout": str,
        "stderr": str,
        "output_dir": "/abs/path/to/output"
    }
    """
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            resp = await client.post(
                BACKEND_URL,
                json={"user_requirement": user_requirement},
            )
            resp.raise_for_status()
            try:
                return resp.json()
            except Exception:
                # Backend responded but not with valid JSON
                return {
                    "error": "Backend did not return valid JSON.",
                    "raw_response": resp.text,
                    "status_code": resp.status_code,
                }
    except httpx.HTTPError as e:
        return {
            "error": f"Failed to reach backend at {BACKEND_URL}",
            "details": repr(e),
        }


def build_file_tree(root_dir: str) -> str:
    """
    Recursively walk root_dir and return a text 'tree' similar to the `tree` command.
    Only directories and filenames are listed (no file contents).
    """
    if not os.path.exists(root_dir):
        return f"[!] Output directory does not exist: {root_dir}"

    if not os.path.isdir(root_dir):
        return f"[!] Output path is not a directory: {root_dir}"

    lines = []

    # We want a simple tree-like display:
    # 📁 .
    #     📁 subdir1/
    #         📄 file1
    #         📄 file2
    #     📁 subdir2/
    #         📄 file3
    for current_root, dirs, files in os.walk(root_dir):
        # Compute indentation level based on relative path depth
        rel_root = os.path.relpath(current_root, root_dir)
        if rel_root == ".":
            depth = 0
            dirname = "."
        else:
            depth = rel_root.count(os.sep) + 1
            dirname = os.path.basename(current_root)

        indent = "    " * depth
        if depth == 0:
            # Top-level folder
            lines.append(f"📁 {dirname}/")
        else:
            lines.append(f"{indent}📁 {dirname}/")

        # Sort to get deterministic ordering
        for fname in sorted(files):
            lines.append(f"{indent}    📄 {fname}")

    return "\n".join(lines)


@cl.on_chat_start
async def on_chat_start():
    """
    Initial system message when the user opens the UI.
    """
    await cl.Message(
        content=(
            "👋 This UI sends your message as `user_requirement` to the Foam-Agent backend.\n\n"
            f"- Backend endpoint: `POST {BACKEND_URL}`\n"
            "- The backend runs Foam-Agent, writes output files, and returns an `output_dir`.\n"
            "- I’ll then list the generated files and directories for you."
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    """
    When the user sends a message:
    1. Forward message.content to the backend as `user_requirement`.
    2. Wait for backend to finish.
    3. Show return code, and a tree of all generated files under output_dir.
    """
    user_text = message.content.strip()

    if not user_text:
        await cl.Message(content="⚠️ Please type a non-empty requirement.").send()
        return

    # Show a "thinking" message like ChatGPT
    running_msg = cl.Message(content="⏳ Running Foam-Agent on your requirement...")
    await running_msg.send()

    # Call backend
    backend_result = await call_backend(user_text)

    # If the backend returned an error, show it nicely
    if "error" in backend_result and "output_dir" not in backend_result:
        pretty = json.dumps(backend_result, indent=2, ensure_ascii=False)
        content = (
            "❌ **Backend error**\n\n"
            "```json\n"
            f"{pretty}\n"
            "```"
        )
        running_msg.content = content
        await running_msg.update()
        return

    # Extract known fields (if present)
    output_dir = backend_result.get("output_dir")
    returncode = backend_result.get("returncode", "N/A")
    stdout = (backend_result.get("stdout") or "").strip()
    stderr = (backend_result.get("stderr") or "").strip()

    # Build directory tree if we have an output_dir
    if output_dir:
        tree = build_file_tree(output_dir)
        tree_block = f"```text\n{tree}\n```"
        header = (
            f"✅ **Foam-Agent finished**\n\n"
            f"- **Return code:** `{returncode}`\n"
            f"- **Output directory:** `{output_dir}`\n\n"
            f"**Generated file tree:**\n{tree_block}"
        )
    else:
        header = (
            "⚠️ Backend did not return an `output_dir` field.\n\n"
            "Here is the raw response:\n\n"
            f"```json\n{json.dumps(backend_result, indent=2, ensure_ascii=False)}\n```"
        )

    # Optionally attach stdout/stderr in collapsible sections
    details_parts = []
    if stdout:
        details_parts.append(
            "<details><summary>📤 STDOUT</summary>\n\n"
            f"```text\n{stdout[:4000]}\n```\n"
            "</details>"
        )
    if stderr:
        details_parts.append(
            "<details><summary>⚠️ STDERR</summary>\n\n"
            f"```text\n{stderr[:4000]}\n```\n"
            "</details>"
        )

    content = header
    if details_parts:
        content += "\n\n" + "\n\n".join(details_parts)

    # Update the "thinking" message with final result
    running_msg.content = content
    await running_msg.update()